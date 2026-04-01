"""LangGraph state definition for the complaint‑processing workflow."""

from __future__ import annotations

from typing import Annotated, Optional

from typing_extensions import TypedDict

from app.schemas.case import CaseRead
from app.schemas.classification import ClassificationResult
from app.schemas.resolution import ResolutionRecommendation
from app.schemas.risk import RiskAssessment


class WorkflowState(TypedDict, total=False):
    """Shared state passed between nodes in the LangGraph workflow.

    Each key is populated by the corresponding agent node and consumed
    by downstream nodes.
    """

    # ── Input ────────────────────────────────────────────────────────────
    raw_payload: dict  # Original API payload

    # ── Intake ───────────────────────────────────────────────────────────
    case: CaseRead

    # ── Classification ───────────────────────────────────────────────────
    classification: ClassificationResult

    # ── Risk ─────────────────────────────────────────────────────────────
    risk_assessment: RiskAssessment

    # ── Resolution ───────────────────────────────────────────────────────
    resolution: ResolutionRecommendation

    # ── Compliance ───────────────────────────────────────────────────────
    compliance: dict  # {"flags": [...], "passed": bool, "notes": ...}

    # ── Review ───────────────────────────────────────────────────────────
    review: dict  # {"decision": ..., "notes": ..., "suggested_changes": ...}

    # ── Routing ──────────────────────────────────────────────────────────
    routed_to: str

    # ── Meta ─────────────────────────────────────────────────────────────
    error: Optional[str]
    retry_count: int
