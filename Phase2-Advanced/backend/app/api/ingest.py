"""
Data Ingestion API Routes
Receives tracking data from desktop agents
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.device import Device
from app.models.activity import AppUsage, IdleInterval
from app.models.presence import PresenceInterval
from app.models.browser_usage import BrowserUsage, DomainRule
from app.schemas.activity import AppUsageCreate, IdleIntervalCreate, AppUsageBatch, IdleIntervalBatch
from app.schemas.presence import PresenceIntervalCreate, PresenceIntervalBatch
from app.schemas.browser_usage import BrowserUsageCreate, BrowserUsageBatch

router = APIRouter()


def validate_device(db: Session, device_id: int, user_id: int) -> Device:
    """Validate device belongs to user"""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.user_id == user_id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or not owned by user"
        )
    
    # Update last seen
    device.last_seen = datetime.utcnow()
    return device


def classify_domain(db: Session, org_id: int, domain: str, dept_id: int = None):
    """Classify domain as productive/unproductive based on rules"""
    rule = db.query(DomainRule).filter(
        DomainRule.org_id == org_id,
        DomainRule.domain == domain
    ).first()
    
    if rule:
        # Check department override
        if dept_id and rule.dept_overrides_json.get(str(dept_id)):
            return rule.category, rule.dept_overrides_json[str(dept_id)]
        return rule.category, rule.label
    
    # Default classification based on common patterns
    unproductive_domains = [
        'facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com',
        'netflix.com', 'youtube.com', 'reddit.com', 'twitch.tv'
    ]
    productive_domains = [
        'github.com', 'gitlab.com', 'stackoverflow.com', 'docs.google.com',
        'notion.so', 'slack.com', 'figma.com', 'jira.atlassian.com'
    ]
    
    if any(d in domain for d in unproductive_domains):
        return "Social/Entertainment", "unproductive"
    elif any(d in domain for d in productive_domains):
        return "Development/Work", "productive"
    
    return "Other", "neutral"


@router.post("/app-usage")
async def ingest_app_usage(
    data: AppUsageBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest batch of app usage records
    """
    if not data.items:
        return {"message": "No data to process", "count": 0}
    
    # Validate device (use first item's device_id)
    device = validate_device(db, data.items[0].device_id, current_user.id)
    
    records = []
    for item in data.items:
        record = AppUsage(
            user_id=current_user.id,
            device_id=item.device_id,
            app_name=item.app_name,
            window_title=item.window_title,
            start_ts=item.start_ts,
            end_ts=item.end_ts,
            duration_sec=item.duration_sec
        )
        records.append(record)
    
    db.add_all(records)
    db.commit()
    
    return {"message": "App usage data ingested", "count": len(records)}


@router.post("/idle-intervals")
async def ingest_idle_intervals(
    data: IdleIntervalBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest batch of idle interval records
    """
    if not data.items:
        return {"message": "No data to process", "count": 0}
    
    device = validate_device(db, data.items[0].device_id, current_user.id)
    
    records = []
    for item in data.items:
        record = IdleInterval(
            user_id=current_user.id,
            device_id=item.device_id,
            start_ts=item.start_ts,
            end_ts=item.end_ts,
            duration_sec=item.duration_sec
        )
        records.append(record)
    
    db.add_all(records)
    db.commit()
    
    return {"message": "Idle intervals ingested", "count": len(records)}


@router.post("/presence-intervals")
async def ingest_presence_intervals(
    data: PresenceIntervalBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest batch of presence interval records
    """
    if not data.items:
        return {"message": "No data to process", "count": 0}
    
    device = validate_device(db, data.items[0].device_id, current_user.id)
    
    records = []
    for item in data.items:
        record = PresenceInterval(
            user_id=current_user.id,
            device_id=item.device_id,
            state=item.state,
            start_ts=item.start_ts,
            end_ts=item.end_ts,
            duration_sec=item.duration_sec
        )
        records.append(record)
    
    db.add_all(records)
    db.commit()
    
    return {"message": "Presence intervals ingested", "count": len(records)}


@router.post("/browser-usage")
async def ingest_browser_usage(
    data: BrowserUsageBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest batch of browser usage records with classification
    """
    if not data.items:
        return {"message": "No data to process", "count": 0}
    
    device = validate_device(db, data.items[0].device_id, current_user.id)
    
    records = []
    for item in data.items:
        # Classify domain
        category, label = classify_domain(
            db, current_user.org_id, item.domain, current_user.dept_id
        )
        
        record = BrowserUsage(
            user_id=current_user.id,
            device_id=item.device_id,
            browser=item.browser,
            domain=item.domain,
            start_ts=item.start_ts,
            end_ts=item.end_ts,
            duration_sec=item.duration_sec,
            category=category,
            label=label
        )
        records.append(record)
    
    db.add_all(records)
    db.commit()
    
    return {"message": "Browser usage ingested", "count": len(records)}
