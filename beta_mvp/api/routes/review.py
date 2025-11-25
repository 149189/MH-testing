from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from db import models as db_models
from monitoring.metrics import record_review_outcome

router = APIRouter(tags=["review"])


class PendingClaim(BaseModel):
    id: int
    claim_id: str
    text: str
    ai_verdict: Optional[str]
    ai_score: Optional[float]
    ai_confidence: Optional[float]


class ReviewDecisionRequest(BaseModel):
    reviewer: Optional[str] = Field(None, description="Reviewer identifier")
    decision: str = Field(..., description="Final human verdict / override text")
    notes: Optional[str] = Field(None, description="Optional reviewer notes")


class ReviewDecisionResponse(BaseModel):
    id: int
    claim_id: str
    final_verdict: str


@router.get("/claims/pending_review", response_model=List[PendingClaim])
async def get_pending_claims(db: Session = Depends(get_db)) -> List[PendingClaim]:
    # Pending = latest verification where overridden == False
    q = (
        db.query(db_models.Verification)
        .filter(db_models.Verification.overridden.is_(False))
        .order_by(db_models.Verification.created_at.desc())
    )

    items: List[PendingClaim] = []
    for v in q.limit(100):
        claim = v.claim
        items.append(
            PendingClaim(
                id=claim.id,
                claim_id=claim.claim_id,
                text=claim.text,
                ai_verdict=v.ai_verdict,
                ai_score=float(v.ai_score) if v.ai_score is not None else None,
                ai_confidence=float(v.ai_confidence) if v.ai_confidence is not None else None,
            )
        )
    return items


@router.post("/claims/{claim_db_id}/decision", response_model=ReviewDecisionResponse)
async def submit_decision(
    claim_db_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> ReviewDecisionResponse:
    claim = db.query(db_models.Claim).filter(db_models.Claim.id == claim_db_id).first()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    # Get latest verification for this claim
    verification = (
        db.query(db_models.Verification)
        .filter(db_models.Verification.claim_id_fk == claim.id)
        .order_by(db_models.Verification.created_at.desc())
        .first()
    )
    if not verification:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No verification found for claim")

    review = db_models.Review(
        claim_id_fk=claim.id,
        verification_id_fk=verification.id,
        reviewer=payload.reviewer,
        decision=payload.decision,
        notes=payload.notes,
    )
    db.add(review)

    verification.overridden = True
    verification.final_verdict = payload.decision

    db.commit()
    db.refresh(verification)

    # Simple TP/FP-style outcome tracking based on agreement with AI verdict
    outcome_label = "other"
    if verification.ai_verdict:
        ai_v = verification.ai_verdict.lower()
        human_v = (payload.decision or "").lower()
        if "true" in ai_v:
            outcome_label = "true_positive" if "true" in human_v else "false_positive"
        elif "false" in ai_v:
            outcome_label = "true_negative" if "false" in human_v else "false_negative"
    record_review_outcome(outcome_label)

    return ReviewDecisionResponse(
        id=claim.id,
        claim_id=claim.claim_id,
        final_verdict=verification.final_verdict or payload.decision,
    )
