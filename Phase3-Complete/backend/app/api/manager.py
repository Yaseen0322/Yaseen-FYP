"""
Manager Dashboard API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_manager
from app.models.user import User
from app.models.activity import AppUsage, IdleInterval
from app.models.presence import PresenceInterval
from app.models.browser_usage import BrowserUsage, DomainRule
from app.schemas.user import UserResponse
from app.schemas.browser_usage import DomainRuleCreate, DomainRuleResponse

router = APIRouter()


@router.get("/employees", response_model=List[UserResponse])
async def list_employees(
    dept_id: Optional[int] = None,
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
    
    employees = query.all()
    return [UserResponse.model_validate(e) for e in employees]


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
        target_date = date.today()
    
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    # Compute summary
    app_time = db.query(func.sum(AppUsage.duration_sec)).filter(
        AppUsage.user_id == employee_id,
        AppUsage.start_ts >= start_dt,
        AppUsage.end_ts <= end_dt
    ).scalar() or 0
    
    idle_time = db.query(func.sum(IdleInterval.duration_sec)).filter(
        IdleInterval.user_id == employee_id,
        IdleInterval.start_ts >= start_dt,
        IdleInterval.end_ts <= end_dt
    ).scalar() or 0
    
    presence_times = db.query(
        PresenceInterval.state,
        func.sum(PresenceInterval.duration_sec)
    ).filter(
        PresenceInterval.user_id == employee_id,
        PresenceInterval.start_ts >= start_dt,
        PresenceInterval.end_ts <= end_dt
    ).group_by(PresenceInterval.state).all()
    
    present_sec = 0
    absent_sec = 0
    camera_off_sec = 0
    for state, duration in presence_times:
        if state == "present":
            present_sec = duration or 0
        elif state == "absent":
            absent_sec = duration or 0
        elif state == "camera_off":
            camera_off_sec = duration or 0
    
    # Productivity
    productivity = db.query(
        BrowserUsage.label,
        func.sum(BrowserUsage.duration_sec)
    ).filter(
        BrowserUsage.user_id == employee_id,
        BrowserUsage.start_ts >= start_dt,
        BrowserUsage.end_ts <= end_dt
    ).group_by(BrowserUsage.label).all()
    
    productive_sec = 0
    unproductive_sec = 0
    for label, duration in productivity:
        if label == "productive":
            productive_sec = duration or 0
        elif label == "unproductive":
            unproductive_sec = duration or 0
    
    # Top apps
    top_apps = db.query(
        AppUsage.app_name,
        func.sum(AppUsage.duration_sec).label('total')
    ).filter(
        AppUsage.user_id == employee_id,
        AppUsage.start_ts >= start_dt,
        AppUsage.end_ts <= end_dt
    ).group_by(AppUsage.app_name).order_by(
        func.sum(AppUsage.duration_sec).desc()
    ).limit(10).all()
    
    # Top domains
    top_domains = db.query(
        BrowserUsage.domain,
        BrowserUsage.label,
        func.sum(BrowserUsage.duration_sec).label('total')
    ).filter(
        BrowserUsage.user_id == employee_id,
        BrowserUsage.start_ts >= start_dt,
        BrowserUsage.end_ts <= end_dt
    ).group_by(BrowserUsage.domain, BrowserUsage.label).order_by(
        func.sum(BrowserUsage.duration_sec).desc()
    ).limit(10).all()
    
    return {
        "employee": UserResponse.model_validate(employee),
        "date": target_date.isoformat(),
        "focus_sec": app_time,
        "idle_sec": idle_time,
        "present_sec": present_sec,
        "absent_sec": absent_sec,
        "camera_off_sec": camera_off_sec,
        "productive_sec": productive_sec,
        "unproductive_sec": unproductive_sec,
        "top_apps": [{"app_name": a, "duration_sec": d} for a, d in top_apps],
        "top_domains": [{"domain": d, "label": l, "duration_sec": dur} for d, l, dur in top_domains]
    }


@router.get("/employees/{employee_id}/timeline")
async def get_employee_timeline(
    employee_id: int,
    target_date: Optional[date] = Query(default=None),
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
        target_date = date.today()
    
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    blocks = []
    
    # Get presence
    presence = db.query(PresenceInterval).filter(
        PresenceInterval.user_id == employee_id,
        PresenceInterval.start_ts >= start_dt,
        PresenceInterval.end_ts <= end_dt
    ).order_by(PresenceInterval.start_ts).all()
    
    for p in presence:
        blocks.append({
            "type": p.state,
            "start_ts": p.start_ts.isoformat(),
            "end_ts": p.end_ts.isoformat(),
            "duration_sec": p.duration_sec
        })
    
    # Get idle
    idles = db.query(IdleInterval).filter(
        IdleInterval.user_id == employee_id,
        IdleInterval.start_ts >= start_dt,
        IdleInterval.end_ts <= end_dt
    ).order_by(IdleInterval.start_ts).all()
    
    for i in idles:
        blocks.append({
            "type": "idle",
            "start_ts": i.start_ts.isoformat(),
            "end_ts": i.end_ts.isoformat(),
            "duration_sec": i.duration_sec
        })

    # Get active app intervals so timeline is useful even when presence data is sparse.
    app_usages = db.query(AppUsage).filter(
        AppUsage.user_id == employee_id,
        AppUsage.start_ts >= start_dt,
        AppUsage.end_ts <= end_dt
    ).order_by(AppUsage.start_ts).all()

    for a in app_usages:
        blocks.append({
            "type": "active",
            "app_name": a.app_name,
            "start_ts": a.start_ts.isoformat(),
            "end_ts": a.end_ts.isoformat(),
            "duration_sec": a.duration_sec
        })
    
    blocks.sort(key=lambda x: x["start_ts"])
    
    return {
        "employee_id": employee_id,
        "date": target_date.isoformat(),
        "blocks": blocks
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
        target_date = date.today()
    
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
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
    
    # Aggregate stats
    total_focus = db.query(func.sum(AppUsage.duration_sec)).filter(
        AppUsage.user_id.in_(employee_ids),
        AppUsage.start_ts >= start_dt,
        AppUsage.end_ts <= end_dt
    ).scalar() or 0
    
    total_idle = db.query(func.sum(IdleInterval.duration_sec)).filter(
        IdleInterval.user_id.in_(employee_ids),
        IdleInterval.start_ts >= start_dt,
        IdleInterval.end_ts <= end_dt
    ).scalar() or 0
    
    total_present = db.query(func.sum(PresenceInterval.duration_sec)).filter(
        PresenceInterval.user_id.in_(employee_ids),
        PresenceInterval.state == "present",
        PresenceInterval.start_ts >= start_dt,
        PresenceInterval.end_ts <= end_dt
    ).scalar() or 0
    
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
    rule = DomainRule(
        org_id=current_user.org_id,
        domain=rule_data.domain,
        category=rule_data.category,
        label=rule_data.label,
        dept_overrides_json=rule_data.dept_overrides_json
    )
    db.add(rule)
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
