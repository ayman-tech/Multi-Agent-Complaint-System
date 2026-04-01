"""Routing agent – determines which team or department handles the case."""

from __future__ import annotations

import logging

from app.schemas.case import CaseRead, CaseStatus
from app.schemas.classification import ClassificationResult, ProductCategory
from app.schemas.risk import RiskAssessment, RiskLevel

logger = logging.getLogger(__name__)

# ── Routing rules ────────────────────────────────────────────────────────────

_PRODUCT_TO_TEAM: dict[ProductCategory, str] = {
    ProductCategory.CREDIT_REPORTING: "credit_reporting_team",
    ProductCategory.DEBT_COLLECTION: "debt_collection_team",
    ProductCategory.MORTGAGE: "mortgage_team",
    ProductCategory.CREDIT_CARD: "credit_card_team",
    ProductCategory.CHECKING_SAVINGS: "banking_team",
    ProductCategory.STUDENT_LOAN: "student_loan_team",
    ProductCategory.VEHICLE_LOAN: "auto_loan_team",
    ProductCategory.PAYDAY_LOAN: "consumer_lending_team",
    ProductCategory.MONEY_TRANSFER: "payments_team",
    ProductCategory.PREPAID_CARD: "payments_team",
    ProductCategory.OTHER: "general_complaints_team",
}


def run_routing(
    case: CaseRead,
    classification: ClassificationResult,
    risk: RiskAssessment,
    review_decision: str = "approve",
) -> str:
    """Determine the destination team for the case.

    Logic
    ─────
    • If the review decision is ``escalate`` → management_escalation_team.
    • If risk_level is critical → executive_complaints_team.
    • Otherwise → map by product_category.
    """
    logger.info("Routing agent running for case %s", case.id)

    if review_decision == "escalate":
        destination = "management_escalation_team"
    elif risk.risk_level == RiskLevel.CRITICAL:
        destination = "executive_complaints_team"
    else:
        destination = _PRODUCT_TO_TEAM.get(
            classification.product_category, "general_complaints_team"
        )

    logger.info("Case %s routed to → %s", case.id, destination)
    return destination
