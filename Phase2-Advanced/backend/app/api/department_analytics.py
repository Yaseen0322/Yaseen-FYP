"""
Department Analytics API Routes - Phase 2
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_manager
from app.models.user import User
from app.models.organization import Department
from app.models.activity import AppUsage, IdleInterval
from app.models.presence import PresenceInterval
from app.models.browser_usage import BrowserUsage

router = APIRouter()


@router.get("/departments/summary")
async def get_all_departments_summary(
    target_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Get summary for all departments"""
    if target_date is None:
        target_date = date.today()
    
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    # Get all departments
    departments = db.query(Department).filter(
        Department.org_id == current_user.org_id
    ).all()
    
    results = []
    for dept in departments:
        # Get employees in department
        employees = db.query(User.id).filter(
            User.org_id == current_user.org_id,
            User.dept_id == dept.id,
            User.role == "employee"
        ).all()
        employee_ids = [e.id for e in employees]
        
        if not employee_ids:
            results.append({
                "department": {"id": dept.id, "name": dept.name},
                "employee_count": 0,
                "total_focus_sec": 0,
                "avg_focus_sec": 0
            })
            continue
        
        # Aggregate stats
        total_focus = db.query(func.sum(AppUsage.duration_sec)).filter(
            AppUsage.user_id.in_(employee_ids),
            AppUsage.start_ts >= start_dt,
            AppUsage.end_ts <= end_dt
        ).scalar() or 0
        
        total_present = db.query(func.sum(PresenceInterval.duration_sec)).filter(
            PresenceInterval.user_id.in_(employee_ids),
            PresenceInterval.state == "present",
            PresenceInterval.start_ts >= start_dt,
            PresenceInterval.end_ts <= end_dt
        ).scalar() or 0
        
        total_idle = db.query(func.sum(IdleInterval.duration_sec)).filter(
            IdleInterval.user_id.in_(employee_ids),
            IdleInterval.start_ts >= start_dt,
            IdleInterval.end_ts <= end_dt
        ).scalar() or 0
        
        # Productivity
        total_productive = db.query(func.sum(BrowserUsage.duration_sec)).filter(
            BrowserUsage.user_id.in_(employee_ids),
            BrowserUsage.label == "productive",
            BrowserUsage.start_ts >= start_dt,
            BrowserUsage.end_ts <= end_dt
        ).scalar() or 0
        
        total_unproductive = db.query(func.sum(BrowserUsage.duration_sec)).filter(
            BrowserUsage.user_id.in_(employee_ids),
            BrowserUsage.label == "unproductive",
            BrowserUsage.start_ts >= start_dt,
            BrowserUsage.end_ts <= end_dt
        ).scalar() or 0
        
        emp_count = len(employee_ids)
        
        results.append({
            "department": {"id": dept.id, "name": dept.name},
            "employee_count": emp_count,
            "total_focus_sec": total_focus,
            "total_present_sec": total_present,
            "total_idle_sec": total_idle,
            "total_productive_sec": total_productive,
            "total_unproductive_sec": total_unproductive,
            "avg_focus_sec": total_focus // emp_count if emp_count else 0,
            "avg_present_sec": total_present // emp_count if emp_count else 0,
            "productivity_ratio": round(
                total_productive / (total_productive + total_unproductive) * 100, 1
            ) if (total_productive + total_unproductive) > 0 else 0
        })
    
    return {
        "date": target_date.isoformat(),
        "departments": results
    }


@router.get("/departments/{dept_id}/details")
async def get_department_details(
    dept_id: int,
    target_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Get detailed analytics for a specific department"""
    if target_date is None:
        target_date = date.today()
    
    # Verify department belongs to org
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.org_id == current_user.org_id
    ).first()
    
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    # Get employees
    employees = db.query(User).filter(
        User.org_id == current_user.org_id,
        User.dept_id == dept_id,
        User.role == "employee",
        User.is_active == True
    ).all()
    
    employee_stats = []
    for emp in employees:
        focus = db.query(func.sum(AppUsage.duration_sec)).filter(
            AppUsage.user_id == emp.id,
            AppUsage.start_ts >= start_dt,
            AppUsage.end_ts <= end_dt
        ).scalar() or 0
        
        present = db.query(func.sum(PresenceInterval.duration_sec)).filter(
            PresenceInterval.user_id == emp.id,
            PresenceInterval.state == "present",
            PresenceInterval.start_ts >= start_dt,
            PresenceInterval.end_ts <= end_dt
        ).scalar() or 0
        
        idle = db.query(func.sum(IdleInterval.duration_sec)).filter(
            IdleInterval.user_id == emp.id,
            IdleInterval.start_ts >= start_dt,
            IdleInterval.end_ts <= end_dt
        ).scalar() or 0
        
        productive = db.query(func.sum(BrowserUsage.duration_sec)).filter(
            BrowserUsage.user_id == emp.id,
            BrowserUsage.label == "productive",
            BrowserUsage.start_ts >= start_dt,
            BrowserUsage.end_ts <= end_dt
        ).scalar() or 0
        
        employee_stats.append({
            "id": emp.id,
            "name": emp.name,
            "email": emp.email,
            "focus_sec": focus,
            "present_sec": present,
            "idle_sec": idle,
            "productive_sec": productive
        })
    
    # Sort by focus time
    employee_stats.sort(key=lambda x: x["focus_sec"], reverse=True)
    
    # Top apps for department
    employee_ids = [e.id for e in employees]
    top_apps = []
    if employee_ids:
        top_apps = db.query(
            AppUsage.app_name,
            func.sum(AppUsage.duration_sec).label('total')
        ).filter(
            AppUsage.user_id.in_(employee_ids),
            AppUsage.start_ts >= start_dt,
            AppUsage.end_ts <= end_dt
        ).group_by(AppUsage.app_name).order_by(
            func.sum(AppUsage.duration_sec).desc()
        ).limit(10).all()
    
    return {
        "department": {"id": dept.id, "name": dept.name},
        "date": target_date.isoformat(),
        "employees": employee_stats,
        "top_apps": [{"app_name": a, "duration_sec": d} for a, d in top_apps]
    }


@router.get("/departments/comparison")
async def compare_departments(
    target_date: Optional[date] = Query(default=None),
    metric: str = Query(default="focus", regex="^(focus|productivity|presence)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Compare departments by a specific metric"""
    if target_date is None:
        target_date = date.today()
    
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    departments = db.query(Department).filter(
        Department.org_id == current_user.org_id
    ).all()
    
    comparison = []
    for dept in departments:
        employees = db.query(User.id).filter(
            User.org_id == current_user.org_id,
            User.dept_id == dept.id,
            User.role == "employee"
        ).all()
        employee_ids = [e.id for e in employees]
        
        if not employee_ids:
            comparison.append({
                "department": dept.name,
                "value": 0,
                "employee_count": 0
            })
            continue
        
        if metric == "focus":
            value = db.query(func.sum(AppUsage.duration_sec)).filter(
                AppUsage.user_id.in_(employee_ids),
                AppUsage.start_ts >= start_dt,
                AppUsage.end_ts <= end_dt
            ).scalar() or 0
            avg_value = value // len(employee_ids)
        elif metric == "presence":
            value = db.query(func.sum(PresenceInterval.duration_sec)).filter(
                PresenceInterval.user_id.in_(employee_ids),
                PresenceInterval.state == "present",
                PresenceInterval.start_ts >= start_dt,
                PresenceInterval.end_ts <= end_dt
            ).scalar() or 0
            avg_value = value // len(employee_ids)
        else:  # productivity
            productive = db.query(func.sum(BrowserUsage.duration_sec)).filter(
                BrowserUsage.user_id.in_(employee_ids),
                BrowserUsage.label == "productive",
                BrowserUsage.start_ts >= start_dt,
                BrowserUsage.end_ts <= end_dt
            ).scalar() or 0
            
            total_browser = db.query(func.sum(BrowserUsage.duration_sec)).filter(
                BrowserUsage.user_id.in_(employee_ids),
                BrowserUsage.start_ts >= start_dt,
                BrowserUsage.end_ts <= end_dt
            ).scalar() or 0
            
            avg_value = round(productive / total_browser * 100) if total_browser > 0 else 0
        
        comparison.append({
            "department": dept.name,
            "value": avg_value if metric != "productivity" else avg_value,
            "employee_count": len(employee_ids)
        })
    
    # Sort by value
    comparison.sort(key=lambda x: x["value"], reverse=True)
    
    return {
        "date": target_date.isoformat(),
        "metric": metric,
        "comparison": comparison
    }


@router.get("/trends/weekly")
async def get_weekly_trends(
    dept_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Get weekly trends for the organization or department"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    # Build employee filter
    emp_query = db.query(User.id).filter(
        User.org_id == current_user.org_id,
        User.role == "employee"
    )
    if dept_id:
        emp_query = emp_query.filter(User.dept_id == dept_id)
    
    employee_ids = [e.id for e in emp_query.all()]
    
    if not employee_ids:
        return {"trends": []}
    
    trends = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        start_dt = datetime.combine(day, datetime.min.time())
        end_dt = datetime.combine(day, datetime.max.time())
        
        focus = db.query(func.sum(AppUsage.duration_sec)).filter(
            AppUsage.user_id.in_(employee_ids),
            AppUsage.start_ts >= start_dt,
            AppUsage.end_ts <= end_dt
        ).scalar() or 0
        
        present = db.query(func.sum(PresenceInterval.duration_sec)).filter(
            PresenceInterval.user_id.in_(employee_ids),
            PresenceInterval.state == "present",
            PresenceInterval.start_ts >= start_dt,
            PresenceInterval.end_ts <= end_dt
        ).scalar() or 0
        
        idle = db.query(func.sum(IdleInterval.duration_sec)).filter(
            IdleInterval.user_id.in_(employee_ids),
            IdleInterval.start_ts >= start_dt,
            IdleInterval.end_ts <= end_dt
        ).scalar() or 0
        
        trends.append({
            "date": day.isoformat(),
            "day": day.strftime("%a"),
            "focus_sec": focus,
            "present_sec": present,
            "idle_sec": idle,
            "avg_focus_sec": focus // len(employee_ids) if employee_ids else 0,
            "avg_present_sec": present // len(employee_ids) if employee_ids else 0
        })
    
    return {
        "week_start": week_start.isoformat(),
        "employee_count": len(employee_ids),
        "trends": trends
    }
