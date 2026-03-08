"""
Employee Reports API Routes
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.activity import AppUsage, IdleInterval
from app.models.presence import PresenceInterval
from app.models.browser_usage import BrowserUsage
from app.models.daily_summary import DailySummary
from app.schemas.reports import (
    TimelineResponse, TimelineBlock,
    AppUsageSummary, DomainUsageSummary, WeeklySummary
)

router = APIRouter()


def _build_summary_payload(user_id: int, target_date: date, summary: DailySummary):
    """
    Normalize precomputed daily summary to the same response contract
    used by on-the-fly summary generation.
    """
    return {
        "user_id": user_id,
        "date": target_date.isoformat(),
        "focus_sec": summary.focus_sec or 0,
        "idle_sec": summary.idle_sec or 0,
        "present_sec": summary.present_sec or 0,
        "absent_sec": summary.absent_sec or 0,
        "camera_off_sec": summary.camera_off_sec or 0,
        "productive_sec": summary.productive_sec or 0,
        "unproductive_sec": summary.unproductive_sec or 0,
        "neutral_sec": summary.neutral_sec or 0,
        "top_apps": summary.top_apps_json or [],
        "top_domains": summary.top_domains_json or []
    }


@router.get("/summary")
async def get_my_summary(
    target_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get daily summary for current user
    """
    if target_date is None:
        target_date = date.today()
    
    # Try to get pre-computed summary
    summary = db.query(DailySummary).filter(
        DailySummary.user_id == current_user.id,
        DailySummary.date == target_date
    ).first()
    
    if summary:
        return _build_summary_payload(current_user.id, target_date, summary)
    
    # Compute summary on-the-fly
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    # Get app usage
    app_time = db.query(func.sum(AppUsage.duration_sec)).filter(
        AppUsage.user_id == current_user.id,
        AppUsage.start_ts >= start_dt,
        AppUsage.end_ts <= end_dt
    ).scalar() or 0
    
    # Get idle time
    idle_time = db.query(func.sum(IdleInterval.duration_sec)).filter(
        IdleInterval.user_id == current_user.id,
        IdleInterval.start_ts >= start_dt,
        IdleInterval.end_ts <= end_dt
    ).scalar() or 0
    
    # Get presence times
    presence_times = db.query(
        PresenceInterval.state,
        func.sum(PresenceInterval.duration_sec)
    ).filter(
        PresenceInterval.user_id == current_user.id,
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
    
    # Get productivity breakdown
    productivity = db.query(
        BrowserUsage.label,
        func.sum(BrowserUsage.duration_sec)
    ).filter(
        BrowserUsage.user_id == current_user.id,
        BrowserUsage.start_ts >= start_dt,
        BrowserUsage.end_ts <= end_dt
    ).group_by(BrowserUsage.label).all()
    
    productive_sec = 0
    unproductive_sec = 0
    neutral_sec = 0
    for label, duration in productivity:
        if label == "productive":
            productive_sec = duration or 0
        elif label == "unproductive":
            unproductive_sec = duration or 0
        else:
            neutral_sec = duration or 0
    
    # Get top apps
    top_apps = db.query(
        AppUsage.app_name,
        func.sum(AppUsage.duration_sec).label('total')
    ).filter(
        AppUsage.user_id == current_user.id,
        AppUsage.start_ts >= start_dt,
        AppUsage.end_ts <= end_dt
    ).group_by(AppUsage.app_name).order_by(
        func.sum(AppUsage.duration_sec).desc()
    ).limit(10).all()
    
    # Get top domains
    top_domains = db.query(
        BrowserUsage.domain,
        BrowserUsage.category,
        BrowserUsage.label,
        func.sum(BrowserUsage.duration_sec).label('total')
    ).filter(
        BrowserUsage.user_id == current_user.id,
        BrowserUsage.start_ts >= start_dt,
        BrowserUsage.end_ts <= end_dt
    ).group_by(
        BrowserUsage.domain,
        BrowserUsage.category,
        BrowserUsage.label
    ).order_by(func.sum(BrowserUsage.duration_sec).desc()).limit(10).all()
    
    return {
        "user_id": current_user.id,
        "date": target_date.isoformat(),
        "focus_sec": app_time,
        "idle_sec": idle_time,
        "present_sec": present_sec,
        "absent_sec": absent_sec,
        "camera_off_sec": camera_off_sec,
        "productive_sec": productive_sec,
        "unproductive_sec": unproductive_sec,
        "neutral_sec": neutral_sec,
        "top_apps": [
            {"app_name": app, "duration_sec": dur}
            for app, dur in top_apps
        ],
        "top_domains": [
            {"domain": d, "category": c, "label": l, "duration_sec": dur}
            for d, c, l, dur in top_domains
        ]
    }


@router.get("/timeline")
async def get_my_timeline(
    target_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get timeline of activities for a day
    """
    if target_date is None:
        target_date = date.today()
    
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    blocks = []
    
    # Get presence intervals
    presence = db.query(PresenceInterval).filter(
        PresenceInterval.user_id == current_user.id,
        PresenceInterval.start_ts >= start_dt,
        PresenceInterval.end_ts <= end_dt
    ).order_by(PresenceInterval.start_ts).all()
    
    for p in presence:
        blocks.append(TimelineBlock(
            type=p.state,
            start_ts=p.start_ts,
            end_ts=p.end_ts,
            duration_sec=p.duration_sec
        ))
    
    # Get idle intervals
    idles = db.query(IdleInterval).filter(
        IdleInterval.user_id == current_user.id,
        IdleInterval.start_ts >= start_dt,
        IdleInterval.end_ts <= end_dt
    ).order_by(IdleInterval.start_ts).all()
    
    for i in idles:
        blocks.append(TimelineBlock(
            type="idle",
            start_ts=i.start_ts,
            end_ts=i.end_ts,
            duration_sec=i.duration_sec
        ))
    
    # Get app usage (aggregated)
    apps = db.query(AppUsage).filter(
        AppUsage.user_id == current_user.id,
        AppUsage.start_ts >= start_dt,
        AppUsage.end_ts <= end_dt
    ).order_by(AppUsage.start_ts).all()
    
    for a in apps:
        blocks.append(TimelineBlock(
            type="app_usage",
            start_ts=a.start_ts,
            end_ts=a.end_ts,
            duration_sec=a.duration_sec,
            details={"app_name": a.app_name}
        ))
    
    # Sort by start time
    blocks.sort(key=lambda x: x.start_ts)
    
    return TimelineResponse(date=target_date, blocks=blocks)


@router.get("/weekly")
async def get_weekly_summary(
    week_offset: int = Query(default=0, description="0 = current week, -1 = last week"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get weekly summary
    """
    today = date.today()
    # Get start of week (Monday)
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    daily_summaries = []
    total_focus = 0
    total_idle = 0
    total_present = 0
    
    for i in range(7):
        day = week_start + timedelta(days=i)
        start_dt = datetime.combine(day, datetime.min.time())
        end_dt = datetime.combine(day, datetime.max.time())
        
        focus = db.query(func.sum(AppUsage.duration_sec)).filter(
            AppUsage.user_id == current_user.id,
            AppUsage.start_ts >= start_dt,
            AppUsage.end_ts <= end_dt
        ).scalar() or 0
        
        idle = db.query(func.sum(IdleInterval.duration_sec)).filter(
            IdleInterval.user_id == current_user.id,
            IdleInterval.start_ts >= start_dt,
            IdleInterval.end_ts <= end_dt
        ).scalar() or 0
        
        present = db.query(func.sum(PresenceInterval.duration_sec)).filter(
            PresenceInterval.user_id == current_user.id,
            PresenceInterval.state == "present",
            PresenceInterval.start_ts >= start_dt,
            PresenceInterval.end_ts <= end_dt
        ).scalar() or 0
        
        daily_summaries.append({
            "date": day.isoformat(),
            "focus_sec": focus,
            "idle_sec": idle,
            "present_sec": present
        })
        
        total_focus += focus
        total_idle += idle
        total_present += present
    
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "daily_summaries": daily_summaries,
        "total_focus_sec": total_focus,
        "total_idle_sec": total_idle,
        "total_present_sec": total_present,
        "avg_daily_focus_sec": total_focus / 7,
        "avg_daily_present_sec": total_present / 7
    }
