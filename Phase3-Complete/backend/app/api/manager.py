"""
Manager Dashboard API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.core.database import get_db
from app.core.dates import utc_today
from app.core.pagination import build_paginated_response
from app.core.security import get_current_manager
from app.models.user import User
from app.models.activity import AppUsage, IdleInterval
from app.models.presence import PresenceInterval
from app.models.browser_usage import BrowserUsage, DomainRule
from app.schemas.user import UserResponse
from app.schemas.browser_usage import DomainRuleCreate, DomainRuleResponse, DomainRuleUpdate
from app.services.reporting import build_daily_summary_response, build_timeline_blocks

router = APIRouter()


@router.get("/employees")
async def list_employees(
    dept_id: Optional[int] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    List all employees (optionally filtered by department)
    """
    query = db.query(User).filter(
        User.org_id == current_user.org_id,
        User.role == "employee"
    )
    
    if dept_id:
        query = query.filter(User.dept_id == dept_id)
    
    total = query.count()
    employees = query.order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit).all()
    return build_paginated_response(
        [UserResponse.model_validate(e).model_dump() for e in employees],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/employees/{employee_id}/summary")
async def get_employee_summary(
    employee_id: int,
    target_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Get summary for specific employee
    """
    # Verify employee belongs to same org
    employee = db.query(User).filter(
        User.id == employee_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if target_date is None:
        target_date = utc_today()
    
    payload = build_daily_summary_response(db, employee_id, target_date)

    return {
        "employee": UserResponse.model_validate(employee),
        **payload,
    }


@router.get("/employees/{employee_id}/timeline")
async def get_employee_timeline(
    employee_id: int,
    target_date: Optional[date] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Get timeline for specific employee
    """
    employee = db.query(User).filter(
        User.id == employee_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if target_date is None:
        target_date = utc_today()
    
    raw_blocks = build_timeline_blocks(db, employee_id, target_date)
    blocks = []
    for block in raw_blocks:
        entry = {
            "type": block["type"],
            "start_ts": block["start_ts"].isoformat(),
            "end_ts": block["end_ts"].isoformat(),
            "duration_sec": block["duration_sec"],
        }
        if block["details"]:
            entry["details"] = block["details"]
        blocks.append(entry)
    
    total = len(blocks)
    paginated_blocks = blocks[offset: offset + limit]

    return {
        "employee_id": employee_id,
        "date": target_date.isoformat(),
        "items": paginated_blocks,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/team-summary")
async def get_team_summary(
    target_date: Optional[date] = Query(default=None),
    dept_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Get aggregated team summary
    """
    if target_date is None:
        target_date = utc_today()
    
    # Get employees query
    emp_query = db.query(User.id).filter(
        User.org_id == current_user.org_id,
        User.role == "employee"
    )
    
    if dept_id:
        emp_query = emp_query.filter(User.dept_id == dept_id)
    
    employee_ids = [e.id for e in emp_query.all()]
    
    if not employee_ids:
        return {"date": target_date.isoformat(), "employee_count": 0}
    
    total_focus = 0
    total_idle = 0
    total_present = 0
    for employee_id in employee_ids:
        payload = build_daily_summary_response(db, employee_id, target_date)
        total_focus += payload["focus_sec"]
        total_idle += payload["idle_sec"]
        total_present += payload["present_sec"]
    
    return {
        "date": target_date.isoformat(),
        "dept_id": dept_id,
        "employee_count": len(employee_ids),
        "total_focus_sec": total_focus,
        "total_idle_sec": total_idle,
        "total_present_sec": total_present,
        "avg_focus_sec": total_focus / len(employee_ids),
        "avg_present_sec": total_present / len(employee_ids)
    }


# Domain rules management
@router.get("/domain-rules", response_model=List[DomainRuleResponse])
async def list_domain_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    List domain classification rules
    """
    rules = db.query(DomainRule).filter(
        DomainRule.org_id == current_user.org_id
    ).all()
    
    return [DomainRuleResponse.model_validate(r) for r in rules]


@router.post("/domain-rules", response_model=DomainRuleResponse)
async def create_domain_rule(
    rule_data: DomainRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Create domain classification rule
    """
    normalized_domain = rule_data.domain.strip().lower()
    existing = db.query(DomainRule).filter(
        DomainRule.org_id == current_user.org_id,
        DomainRule.domain == normalized_domain
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A rule for that domain already exists")

    rule = DomainRule(
        org_id=current_user.org_id,
        domain=normalized_domain,
        category=rule_data.category,
        label=rule_data.label,
        dept_overrides_json=rule_data.dept_overrides_json
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return DomainRuleResponse.model_validate(rule)


@router.patch("/domain-rules/{rule_id}", response_model=DomainRuleResponse)
async def update_domain_rule(
    rule_id: int,
    rule_data: DomainRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Update domain classification rule
    """
    rule = db.query(DomainRule).filter(
        DomainRule.id == rule_id,
        DomainRule.org_id == current_user.org_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = rule_data.model_dump(exclude_unset=True)
    if "domain" in update_data and update_data["domain"]:
        normalized_domain = update_data["domain"].strip().lower()
        existing = db.query(DomainRule).filter(
            DomainRule.org_id == current_user.org_id,
            DomainRule.domain == normalized_domain,
            DomainRule.id != rule.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="A rule for that domain already exists")
        update_data["domain"] = normalized_domain

    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return DomainRuleResponse.model_validate(rule)


@router.delete("/domain-rules/{rule_id}")
async def delete_domain_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Delete domain classification rule
    """
    rule = db.query(DomainRule).filter(
        DomainRule.id == rule_id,
        DomainRule.org_id == current_user.org_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    
    return {"message": "Rule deleted"}
