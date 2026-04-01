"""Pydantic models for complaint classification output."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProductCategory(str, Enum):
    CREDIT_REPORTING = "credit_reporting"
    DEBT_COLLECTION = "debt_collection"
    MORTGAGE = "mortgage"
    CREDIT_CARD = "credit_card"
    CHECKING_SAVINGS = "checking_savings"
    STUDENT_LOAN = "student_loan"
    VEHICLE_LOAN = "vehicle_loan"
    PAYDAY_LOAN = "payday_loan"
    MONEY_TRANSFER = "money_transfer"
    PREPAID_CARD = "prepaid_card"
    OTHER = "other"


class IssueType(str, Enum):
    INCORRECT_INFO = "incorrect_information"
    COMMUNICATION_TACTICS = "communication_tactics"
    ACCOUNT_MANAGEMENT = "account_management"
    BILLING_DISPUTES = "billing_disputes"
    FRAUD_SCAM = "fraud_or_scam"
    LOAN_MODIFICATION = "loan_modification"
    PAYMENT_PROCESSING = "payment_processing"
    DISCLOSURE_TRANSPARENCY = "disclosure_transparency"
    CLOSING_CANCELLING = "closing_or_cancelling"
    OTHER = "other"


class ClassificationResult(BaseModel):
    """Structured output produced by the classification agent."""

    product_category: ProductCategory
    issue_type: IssueType
    sub_issue: Optional[str] = None
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence score"
    )
    reasoning: str = Field(
        ..., description="Brief chain‑of‑thought justification"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Key phrases extracted from the narrative",
    )
