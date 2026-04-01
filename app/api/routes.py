"""FastAPI routes for the complaint‑processing service."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.db.session import get_db
from app.db.models import ComplaintCase
from app.orchestrator.workflow import process_complaint
from app.schemas.case import CaseCreate, CaseRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["complaints"])


@router.post(
    "/complaints",
    response_model=CaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new consumer complaint",
)
async def create_complaint(payload: CaseCreate) -> CaseRead:
    """Accept a complaint, run it through the full agent pipeline, and return
    the enriched case with classification, risk, resolution, and routing."""
    try:
        final_state = process_complaint(payload.model_dump())
        case: CaseRead = final_state["case"]

        # Persist to database
        with get_db() as db:
            db_case = ComplaintCase(
                id=case.id,
                status=case.status.value,
                consumer_narrative=case.consumer_narrative,
                product=case.product,
                sub_product=case.sub_product,
                company=case.company,
                state=case.state,
                zip_code=case.zip_code,
                channel=case.channel.value,
                submitted_at=case.submitted_at,
            )
            db.add(db_case)

        return case

    except Exception as exc:
        logger.exception("Failed to process complaint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Complaint processing failed: {exc}",
        ) from exc


@router.get(
    "/complaints/{case_id}",
    response_model=CaseRead,
    summary="Retrieve a complaint by ID",
)
async def get_complaint(case_id: str) -> CaseRead:
    """Fetch a previously processed complaint case."""
    with get_db() as db:
        db_case = db.query(ComplaintCase).filter(ComplaintCase.id == case_id).first()
        if db_case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )
        return CaseRead.model_validate(db_case)


@router.get(
    "/complaints",
    response_model=list[CaseRead],
    summary="List recent complaints",
)
async def list_complaints(limit: int = 20, offset: int = 0) -> list[CaseRead]:
    """Return a paginated list of complaint cases."""
    with get_db() as db:
        rows = (
            db.query(ComplaintCase)
            .order_by(ComplaintCase.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [CaseRead.model_validate(row) for row in rows]


@router.get("/health", summary="Health check")
async def health_check() -> dict:
    return {"status": "ok"}
