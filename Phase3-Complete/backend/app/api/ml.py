"""
ML Classification API Routes - Phase 3
Review and approve ML-assisted classifications
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.pagination import build_paginated_response
from app.core.security import get_current_manager
from app.models.user import User
from app.models.integrations import MLClassification
from app.services.ml_classifier import get_classifier

router = APIRouter()


class MLClassificationResponse(BaseModel):
    id: int
    org_id: int
    classification_type: str
    input_value: str
    predicted_category: Optional[str]
    predicted_label: Optional[str]
    confidence: Optional[int]
    is_approved: bool
    approved_by: Optional[int]

    class Config:
        from_attributes = True


class MLApprovalRequest(BaseModel):
    label: Optional[str] = None


@router.get("/classifications")
async def list_classifications(
    status: str = Query(default="pending", pattern="^(pending|approved|all)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    """
    List ML classifications for manager review.
    """
    query = db.query(MLClassification).filter(
        MLClassification.org_id == current_user.org_id
    )

    if status == "pending":
        query = query.filter(MLClassification.is_approved == False)
    elif status == "approved":
        query = query.filter(MLClassification.is_approved == True)

    total = query.count()
    items = query.order_by(MLClassification.created_at.desc(), MLClassification.id.desc()).offset(offset).limit(limit).all()
    return build_paginated_response(
        [MLClassificationResponse.model_validate(item).model_dump() for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/classifications/{classification_id}/approve")
async def approve_classification(
    classification_id: int,
    payload: MLApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    """
    Approve or correct a predicted label for a classification.
    """
    item = db.query(MLClassification).filter(
        MLClassification.id == classification_id,
        MLClassification.org_id == current_user.org_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Classification not found")

    classifier = get_classifier(db)
    classifier.approve_classification(
        classification_id=classification_id,
        user_id=current_user.id,
        approved_label=payload.label
    )

    return {"message": "Classification approved"}


@router.delete("/classifications/{classification_id}")
async def delete_classification(
    classification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager),
):
    """
    Remove a classification record (e.g., rejected suggestion).
    """
    item = db.query(MLClassification).filter(
        MLClassification.id == classification_id,
        MLClassification.org_id == current_user.org_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Classification not found")

    db.delete(item)
    db.commit()

    return {"message": "Classification deleted"}
