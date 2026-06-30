"""
Employee Reports API Routes
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.core.database import get_db
from app.core.dates import utc_today
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
from app.services.reporting import (
    build_daily_summary_response,
    build_timeline_blocks,
    upsert_daily_summary,
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
        target_date = utc_today()
    
    # Use pre-computed summary only for historical dates.
    # For today, compute live so dashboard reflects near real-time tracking changes.
    if target_date != utc_today():
        summary = db.query(DailySummary).filter(
            DailySummary.user_id == current_user.id,
            DailySummary.date == target_date
        ).first()
        
        if summary:
            return _build_summary_payload(current_user.id, target_date, summary)

    return build_daily_summary_response(db, current_user.id, target_date)


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
        target_date = utc_today()
    
    blocks = [
        TimelineBlock(**block)
        for block in build_timeline_blocks(db, current_user.id, target_date)
    ]
    
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
    today = utc_today()
    # Get start of week (Monday)
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    daily_summaries = []
    total_focus = 0
    total_idle = 0
    total_present = 0

    precomputed = db.query(DailySummary).filter(
        DailySummary.user_id == current_user.id,
        DailySummary.date >= week_start,
        DailySummary.date <= week_end
    ).all()
    precomputed_by_date = {item.date: item for item in precomputed}

    for i in range(7):
        day = week_start + timedelta(days=i)
        summary = precomputed_by_date.get(day)
        # Keep current day live to avoid stale "today" values in weekly report.
        if summary and day != today:
            focus = summary.focus_sec or 0
            idle = summary.idle_sec or 0
            present = summary.present_sec or 0
        else:
            payload = build_daily_summary_response(db, current_user.id, day)
            if day != today:
                upsert_daily_summary(db, current_user.id, day)
                db.commit()
            focus = payload["focus_sec"]
            idle = payload["idle_sec"]
            present = payload["present_sec"]
        
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
