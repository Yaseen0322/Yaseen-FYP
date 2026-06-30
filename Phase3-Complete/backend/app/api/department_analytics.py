"""
Department analytics API routes.
"""
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dates import as_utc, utc_today
from app.core.security import get_current_manager
from app.models.activity import AppUsage
from app.models.daily_summary import DailySummary
from app.models.organization import Department
from app.models.user import User
from app.services.reporting import get_day_bounds

router = APIRouter()


def _db_query_ts(db: Session, value):
    utc_value = as_utc(value)
    if db.bind and db.bind.dialect.name == "sqlite":
        return utc_value.replace(tzinfo=None)
    return utc_value


def _employee_counts_subquery(db: Session, org_id: int):
    return db.query(
        User.dept_id.label("dept_id"),
        func.count(User.id).label("employee_count"),
    ).filter(
        User.org_id == org_id,
        User.role == "employee",
        User.is_active == True,
        User.dept_id.isnot(None),
    ).group_by(User.dept_id).subquery()


def _department_summary_subquery(db: Session, org_id: int, target_date: date):
    return db.query(
        User.dept_id.label("dept_id"),
        func.coalesce(func.sum(DailySummary.focus_sec), 0).label("total_focus_sec"),
        func.coalesce(func.sum(DailySummary.present_sec), 0).label("total_present_sec"),
        func.coalesce(func.sum(DailySummary.idle_sec), 0).label("total_idle_sec"),
        func.coalesce(func.sum(DailySummary.productive_sec), 0).label("total_productive_sec"),
        func.coalesce(func.sum(DailySummary.unproductive_sec), 0).label("total_unproductive_sec"),
    ).join(
        DailySummary,
        and_(DailySummary.user_id == User.id, DailySummary.date == target_date),
        isouter=True,
    ).filter(
        User.org_id == org_id,
        User.role == "employee",
        User.is_active == True,
        User.dept_id.isnot(None),
    ).group_by(User.dept_id).subquery()


@router.get("/departments/summary")
async def get_all_departments_summary(
    target_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Get summary for all departments."""
    if target_date is None:
        target_date = utc_today()

    employee_counts = _employee_counts_subquery(db, current_user.org_id)
    summary_totals = _department_summary_subquery(db, current_user.org_id, target_date)

    rows = db.query(
        Department.id,
        Department.name,
        func.coalesce(employee_counts.c.employee_count, 0).label("employee_count"),
        func.coalesce(summary_totals.c.total_focus_sec, 0).label("total_focus_sec"),
        func.coalesce(summary_totals.c.total_present_sec, 0).label("total_present_sec"),
        func.coalesce(summary_totals.c.total_idle_sec, 0).label("total_idle_sec"),
        func.coalesce(summary_totals.c.total_productive_sec, 0).label("total_productive_sec"),
        func.coalesce(summary_totals.c.total_unproductive_sec, 0).label("total_unproductive_sec"),
    ).filter(
        Department.org_id == current_user.org_id
    ).outerjoin(
        employee_counts, employee_counts.c.dept_id == Department.id
    ).outerjoin(
        summary_totals, summary_totals.c.dept_id == Department.id
    ).order_by(Department.name.asc()).all()

    results = []
    for row in rows:
        total_browser = row.total_productive_sec + row.total_unproductive_sec
        results.append({
            "department": {"id": row.id, "name": row.name},
            "employee_count": row.employee_count,
            "total_focus_sec": row.total_focus_sec,
            "total_present_sec": row.total_present_sec,
            "total_idle_sec": row.total_idle_sec,
            "total_productive_sec": row.total_productive_sec,
            "total_unproductive_sec": row.total_unproductive_sec,
            "avg_focus_sec": row.total_focus_sec // row.employee_count if row.employee_count else 0,
            "avg_present_sec": row.total_present_sec // row.employee_count if row.employee_count else 0,
            "productivity_ratio": round((row.total_productive_sec / total_browser) * 100, 1) if total_browser else 0,
        })

    return {
        "date": target_date.isoformat(),
        "departments": results,
    }


@router.get("/departments/{dept_id}/details")
async def get_department_details(
    dept_id: int,
    target_date: Optional[date] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Get detailed analytics for a specific department."""
    if target_date is None:
        target_date = utc_today()

    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.org_id == current_user.org_id
    ).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    focus_expr = func.coalesce(DailySummary.focus_sec, 0)
    present_expr = func.coalesce(DailySummary.present_sec, 0)
    idle_expr = func.coalesce(DailySummary.idle_sec, 0)
    productive_expr = func.coalesce(DailySummary.productive_sec, 0)

    employee_query = db.query(
        User.id.label("id"),
        User.name.label("name"),
        User.email.label("email"),
        focus_expr.label("focus_sec"),
        present_expr.label("present_sec"),
        idle_expr.label("idle_sec"),
        productive_expr.label("productive_sec"),
    ).outerjoin(
        DailySummary,
        and_(DailySummary.user_id == User.id, DailySummary.date == target_date),
    ).filter(
        User.org_id == current_user.org_id,
        User.dept_id == dept_id,
        User.role == "employee",
        User.is_active == True,
    )

    total_employees = employee_query.count()
    employee_rows = employee_query.order_by(
        focus_expr.desc(),
        User.id.desc(),
    ).offset(offset).limit(limit).all()

    employee_ids = [
        row[0]
        for row in db.query(User.id).filter(
            User.org_id == current_user.org_id,
            User.dept_id == dept_id,
            User.role == "employee",
            User.is_active == True,
        ).all()
    ]

    top_apps = []
    if employee_ids:
        range_start, range_end = get_day_bounds(target_date)
        app_totals = defaultdict(int)
        app_rows = db.query(
            AppUsage.app_name,
            AppUsage.start_ts,
            AppUsage.end_ts,
        ).filter(
            AppUsage.user_id.in_(employee_ids),
            AppUsage.start_ts < _db_query_ts(db, range_end),
            AppUsage.end_ts > _db_query_ts(db, range_start),
        ).all()

        for app_name, start_ts, end_ts in app_rows:
            clipped_start = max(as_utc(start_ts), as_utc(range_start))
            clipped_end = min(as_utc(end_ts), as_utc(range_end))
            duration_sec = int((clipped_end - clipped_start).total_seconds())
            if duration_sec > 0:
                app_totals[app_name] += duration_sec

        top_apps = [
            {"app_name": app_name, "duration_sec": duration_sec}
            for app_name, duration_sec in sorted(
                app_totals.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:10]
        ]

    return {
        "department": {"id": dept.id, "name": dept.name},
        "date": target_date.isoformat(),
        "employees": [
            {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "focus_sec": row.focus_sec,
                "present_sec": row.present_sec,
                "idle_sec": row.idle_sec,
                "productive_sec": row.productive_sec,
            }
            for row in employee_rows
        ],
        "employees_total": total_employees,
        "employees_limit": limit,
        "employees_offset": offset,
        "top_apps": top_apps,
    }


@router.get("/departments/comparison")
async def compare_departments(
    target_date: Optional[date] = Query(default=None),
    metric: str = Query(default="focus", pattern="^(focus|productivity|presence)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Compare departments by a specific metric."""
    if target_date is None:
        target_date = utc_today()

    employee_counts = _employee_counts_subquery(db, current_user.org_id)
    summary_totals = _department_summary_subquery(db, current_user.org_id, target_date)

    rows = db.query(
        Department.name.label("department"),
        func.coalesce(employee_counts.c.employee_count, 0).label("employee_count"),
        func.coalesce(summary_totals.c.total_focus_sec, 0).label("total_focus_sec"),
        func.coalesce(summary_totals.c.total_present_sec, 0).label("total_present_sec"),
        func.coalesce(summary_totals.c.total_productive_sec, 0).label("total_productive_sec"),
        func.coalesce(summary_totals.c.total_unproductive_sec, 0).label("total_unproductive_sec"),
    ).filter(
        Department.org_id == current_user.org_id
    ).outerjoin(
        employee_counts, employee_counts.c.dept_id == Department.id
    ).outerjoin(
        summary_totals, summary_totals.c.dept_id == Department.id
    ).all()

    comparison = []
    for row in rows:
        if metric == "focus":
            value = row.total_focus_sec // row.employee_count if row.employee_count else 0
        elif metric == "presence":
            value = row.total_present_sec // row.employee_count if row.employee_count else 0
        else:
            total_browser = row.total_productive_sec + row.total_unproductive_sec
            value = round((row.total_productive_sec / total_browser) * 100) if total_browser else 0

        comparison.append({
            "department": row.department,
            "value": value,
            "employee_count": row.employee_count,
        })

    comparison.sort(key=lambda item: item["value"], reverse=True)

    return {
        "date": target_date.isoformat(),
        "metric": metric,
        "comparison": comparison,
    }


@router.get("/trends/weekly")
async def get_weekly_trends(
    dept_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Get weekly trends for the organization or a single department."""
    today = utc_today()
    week_start = today - timedelta(days=today.weekday())

    employee_filter = [
        User.org_id == current_user.org_id,
        User.role == "employee",
        User.is_active == True,
    ]
    if dept_id:
        employee_filter.append(User.dept_id == dept_id)

    employee_count = db.query(func.count(User.id)).filter(*employee_filter).scalar() or 0
    if not employee_count:
        return {"trends": []}

    rows = db.query(
        DailySummary.date.label("summary_date"),
        func.coalesce(func.sum(DailySummary.focus_sec), 0).label("total_focus_sec"),
        func.coalesce(func.sum(DailySummary.present_sec), 0).label("total_present_sec"),
        func.coalesce(func.sum(DailySummary.idle_sec), 0).label("total_idle_sec"),
    ).join(
        User, User.id == DailySummary.user_id
    ).filter(
        *employee_filter,
        DailySummary.date >= week_start,
        DailySummary.date <= week_start + timedelta(days=6),
    ).group_by(
        DailySummary.date
    ).all()

    rows_by_date = {row.summary_date: row for row in rows}
    trends = []
    for index in range(7):
        current_day = week_start + timedelta(days=index)
        row = rows_by_date.get(current_day)
        total_focus = row.total_focus_sec if row else 0
        total_present = row.total_present_sec if row else 0
        total_idle = row.total_idle_sec if row else 0

        trends.append({
            "date": current_day.isoformat(),
            "day": current_day.strftime("%a"),
            "focus_sec": total_focus,
            "present_sec": total_present,
            "idle_sec": total_idle,
            "avg_focus_sec": total_focus // employee_count if employee_count else 0,
            "avg_present_sec": total_present // employee_count if employee_count else 0,
        })

    return {
        "week_start": week_start.isoformat(),
        "employee_count": employee_count,
        "trends": trends,
    }
