"""
User Management API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.pagination import build_paginated_response
from app.core.security import get_current_user, get_current_manager, get_password_hash
from app.models.user import User
from app.schemas.user import UserResponse, UserCreate, UserUpdate

router = APIRouter()


def _can_manage_role(actor: User, role: str) -> bool:
    if actor.role == "super_admin":
        return True
    if actor.role == "admin":
        return role in {"employee", "manager", "admin"}
    if actor.role == "manager":
        return role == "employee"
    return False


def _assert_can_create_role(actor: User, role: str):
    if not _can_manage_role(actor, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to assign that role"
        )


def _assert_can_manage_target(actor: User, target: User):
    if actor.role == "super_admin":
        return

    if actor.role == "admin":
        if target.role == "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access cannot manage super admins"
            )
        return

    if actor.role == "manager" and target.role != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers can only manage employee accounts"
        )


@router.get("/")
async def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    List all users in organization (Manager only)
    """
    query = db.query(User).filter(User.org_id == current_user.org_id)
    if current_user.role == "manager":
        query = query.filter(User.role == "employee")
    elif current_user.role == "admin":
        query = query.filter(User.role != "super_admin")

    total = query.count()
    users = query.order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit).all()
    
    return build_paginated_response(
        [UserResponse.model_validate(u).model_dump() for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Create new user (Manager only)
    """
    # Check if email exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    _assert_can_create_role(current_user, user_data.role)
    
    hashed_password = get_password_hash(user_data.password)
    user = User(
        org_id=current_user.org_id,
        email=user_data.email,
        name=user_data.name,
        employee_id=user_data.employee_id,
        dept_id=user_data.dept_id,
        hashed_password=hashed_password,
        role=user_data.role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Get user by ID (Manager only)
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _assert_can_manage_target(current_user, user)
    
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Update user (Manager only)
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _assert_can_manage_target(current_user, user)
    
    update_data = user_data.model_dump(exclude_unset=True)
    if "role" in update_data:
        _assert_can_create_role(current_user, update_data["role"])

    if "status" in update_data:
        if update_data["status"] == "inactive":
            update_data["is_active"] = False
        elif update_data["status"] == "active":
            update_data["is_active"] = True

    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Deactivate user (Manager only)
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _assert_can_manage_target(current_user, user)
    if current_user.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    user.is_active = False
    user.status = "inactive"
    db.commit()
    
    return {"message": "User deactivated"}
