"""LangGraph workflow that orchestrates all complaint‑processing agents."""

from __future__ import annotations

import json
import logging

from langgraph.graph import END, StateGraph

from app.agents.classification import run_classification
from app.agents.compliance import run_compliance_check
from app.agents.intake import run_intake
from app.agents.resolution import run_resolution
from app.agents.review import run_review
from app.agents.risk import run_risk_assessment
from app.agents.routing import run_routing
from app.orchestrator.rules import (
    low_confidence_gate,
    needs_compliance_review,
    review_decision_router,
)
from app.orchestrator.state import WorkflowState
from app.retrieval.complaint_index import ComplaintIndex
from app.retrieval.resolution_index import ResolutionIndex
from app.schemas.case import CaseCreate, CaseStatus

logger = logging.getLogger(__name__)

# ── Lazy retrieval indices (avoid loading embedding models at import time) ──
_complaint_index: ComplaintIndex | None = None
_resolution_index: ResolutionIndex | None = None


def _complaint_index_singleton() -> ComplaintIndex:
    global _complaint_index
    if _complaint_index is None:
        _complaint_index = ComplaintIndex()
    return _complaint_index


def _resolution_index_singleton() -> ResolutionIndex:
    global _resolution_index
    if _resolution_index is None:
        _resolution_index = ResolutionIndex()
    return _resolution_index


# ── Node functions ───────────────────────────────────────────────────────────

def intake_node(state: WorkflowState) -> WorkflowState:
    payload = CaseCreate(**state["raw_payload"])
    case = run_intake(payload)
    return {**state, "case": case}


def classify_node(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    result = run_classification(
        narrative=case.consumer_narrative,
        product=case.product,
        sub_product=case.sub_product,
        company=case.company,
        state=case.state,
        complaint_index=_complaint_index_singleton(),
    )
    case.classification = result.model_dump()
    case.status = CaseStatus.CLASSIFIED
    return {**state, "case": case, "classification": result}


def risk_node(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    result = run_risk_assessment(
        narrative=case.consumer_narrative,
        classification=state["classification"],
        complaint_index=_complaint_index_singleton(),
    )
    case.risk_assessment = result.model_dump()
    case.status = CaseStatus.RISK_ASSESSED
    return {**state, "case": case, "risk_assessment": result}


def resolution_node(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    result = run_resolution(
        narrative=case.consumer_narrative,
        classification=state["classification"],
        risk=state["risk_assessment"],
        resolution_index=_resolution_index_singleton(),
    )
    case.proposed_resolution = result.model_dump()
    case.status = CaseStatus.RESOLUTION_PROPOSED
    return {**state, "case": case, "resolution": result}


def compliance_node(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    result = run_compliance_check(
        narrative=case.consumer_narrative,
        classification=state["classification"],
        risk=state["risk_assessment"],
        resolution=state["resolution"],
    )
    case.compliance_flags = result.get("flags", [])
    case.status = CaseStatus.COMPLIANCE_CHECKED
    return {**state, "case": case, "compliance": result}


def review_node(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    result = run_review(
        narrative=case.consumer_narrative,
        classification_json=json.dumps(state["classification"].model_dump()),
        risk_json=json.dumps(state["risk_assessment"].model_dump()),
        resolution_json=json.dumps(state["resolution"].model_dump()),
        compliance_json=json.dumps(state.get("compliance", {})),
    )
    case.review_notes = result.get("notes", "")
    case.status = CaseStatus.REVIEWED
    return {**state, "case": case, "review": result}


def routing_node(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    destination = run_routing(
        case=case,
        classification=state["classification"],
        risk=state["risk_assessment"],
        review_decision=state.get("review", {}).get("decision", "approve"),
    )
    case.routed_to = destination
    case.status = CaseStatus.ROUTED
    return {**state, "case": case, "routed_to": destination}


# ── Conditional‑edge helpers (must return node names) ────────────────────────

def _confidence_router(state: WorkflowState) -> str:
    return low_confidence_gate(state)


def _compliance_router(state: WorkflowState) -> str:
    if needs_compliance_review(state):
        return "compliance"
    return "review"


def _review_router(state: WorkflowState) -> str:
    return review_decision_router(state)


# ── Build the graph ──────────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """Construct and return the compiled LangGraph workflow."""

    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("intake", intake_node)
    graph.add_node("classify", classify_node)
    graph.add_node("risk", risk_node)
    graph.add_node("resolution", resolution_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("review", review_node)
    graph.add_node("route", routing_node)

    # Set entry point
    graph.set_entry_point("intake")

    # Linear edges
    graph.add_edge("intake", "classify")

    # Conditional: after classification, check confidence
    graph.add_conditional_edges(
        "classify",
        _confidence_router,
        {"continue": "risk", "reclassify": "classify"},
    )

    graph.add_edge("risk", "resolution")

    # Conditional: after resolution, decide if compliance check is needed
    graph.add_conditional_edges(
        "resolution",
        _compliance_router,
        {"compliance": "compliance", "review": "review"},
    )

    graph.add_edge("compliance", "review")

    # Conditional: after review, decide next step
    graph.add_conditional_edges(
        "review",
        _review_router,
        {"route": "route", "revise": "resolution", "escalate": "route"},
    )

    graph.add_edge("route", END)

    return graph.compile()


# ── Convenience runner ───────────────────────────────────────────────────────

workflow = build_workflow()


def process_complaint(payload: dict) -> WorkflowState:
    """Run the full complaint pipeline and return the final state."""
    initial_state: WorkflowState = {
        "raw_payload": payload,
        "retry_count": 0,
    }
    final_state = workflow.invoke(initial_state)
    logger.info("Workflow complete – routed to %s", final_state.get("routed_to"))
    return final_state
