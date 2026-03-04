"""
ML Classification API Routes - Phase 3
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_manager
from app.models.integrations import MLClassification
from app.models.user import User
from app.services.ml_classifier import get_classifier

router = APIRouter()


class MLClassificationResponse(BaseModel):
    id: int
    classification_type: str
    input_value: str
    predicted_category: Optional[str]
    predicted_label: Optional[str]
    confidence: Optional[int]
    is_approved: bool

    class Config:
        from_attributes = True


class MLApprovePayload(BaseModel):
    label: Optional[str] = None


@router.get("/classifications", response_model=List[MLClassificationResponse])
async def list_classifications(
    status: str = Query(default="pending", pattern="^(pending|approved|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    """
    List ML classifications for current organization.
    """
    query = db.query(MLClassification).filter(MLClassification.org_id == current_user.org_id)

    if status == "pending":
        query = query.filter(MLClassification.is_approved.is_(False))
    elif status == "approved":
        query = query.filter(MLClassification.is_approved.is_(True))

    return query.order_by(MLClassification.created_at.desc()).limit(200).all()


@router.post("/classifications/{classification_id}/approve")
async def approve_classification(
    classification_id: int,
    payload: MLApprovePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    """
    Approve or correct an ML classification.
    """
    classification = db.query(MLClassification).filter(
        MLClassification.id == classification_id,
        MLClassification.org_id == current_user.org_id,
    ).first()
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    classifier = get_classifier(db)
    classifier.approve_classification(
        classification_id=classification_id,
        user_id=current_user.id,
        approved_label=payload.label,
    )

    return {"message": "Classification approved"}


@router.delete("/classifications/{classification_id}")
async def delete_classification(
    classification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    """
    Delete an ML classification record.
    """
    classification = db.query(MLClassification).filter(
        MLClassification.id == classification_id,
        MLClassification.org_id == current_user.org_id,
    ).first()
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    db.delete(classification)
    db.commit()
    return {"message": "Classification deleted"}
