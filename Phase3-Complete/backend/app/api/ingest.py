"""
Data Ingestion API Routes
Receives tracking data from desktop agents
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Iterable
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.core.dates import to_app_timezone
from app.core.security import get_current_user
from app.models.user import User
from app.models.device import Device
from app.models.activity import AppUsage, IdleInterval
from app.models.presence import PresenceInterval
from app.models.browser_usage import BrowserUsage, DomainRule
from app.schemas.activity import AppUsageBatch, IdleIntervalBatch
from app.schemas.presence import PresenceIntervalBatch
from app.schemas.browser_usage import BrowserUsageBatch
from app.services.ml_classifier import get_classifier
from app.services.reporting import refresh_daily_summaries

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
    device.last_seen = datetime.now(timezone.utc)
    return device

def validate_batch_items(items: Iterable, current_user: User, db: Session) -> Device:
    items = list(items)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to process",
        )

    device_id = items[0].device_id
    if any(item.device_id != device_id for item in items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All items in a batch must use the same device_id",
        )

    device = validate_device(db, device_id, current_user.id)

    for item in items:
        if item.end_ts <= item.start_ts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_ts must be greater than start_ts",
            )

        expected_duration = int((item.end_ts - item.start_ts).total_seconds())
        if item.duration_sec <= 0 or item.duration_sec != expected_duration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="duration_sec must match the interval between start_ts and end_ts",
            )

    return device


def get_affected_dates(items: Iterable) -> set:
    affected_dates = set()
    for item in items:
        current_date = to_app_timezone(item.start_ts).date()
        last_date = to_app_timezone(item.end_ts - timedelta(seconds=1)).date()
        while current_date <= last_date:
            affected_dates.add(current_date)
            current_date += timedelta(days=1)
    return affected_dates


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
    
    device = validate_batch_items(data.items, current_user, db)
    classifier = get_classifier(db)
    
    rows = [
        {
            "user_id": current_user.id,
            "device_id": device.id,
            "app_name": item.app_name,
            "window_title": item.window_title,
            "start_ts": item.start_ts,
            "end_ts": item.end_ts,
            "duration_sec": item.duration_sec
        }
        for item in data.items
    ]

    for app_name in {item.app_name.strip() for item in data.items if item.app_name and item.app_name.strip()}:
        classifier.classify_app(app_name=app_name, org_id=current_user.org_id)

    db.bulk_insert_mappings(AppUsage, rows)
    refresh_daily_summaries(db, current_user.id, get_affected_dates(data.items))
    db.commit()
    
    return {"message": "App usage data ingested", "count": len(rows)}


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
    
    device = validate_batch_items(data.items, current_user, db)
    
    rows = [
        {
            "user_id": current_user.id,
            "device_id": device.id,
            "start_ts": item.start_ts,
            "end_ts": item.end_ts,
            "duration_sec": item.duration_sec
        }
        for item in data.items
    ]

    db.bulk_insert_mappings(IdleInterval, rows)
    refresh_daily_summaries(db, current_user.id, get_affected_dates(data.items))
    db.commit()
    
    return {"message": "Idle intervals ingested", "count": len(rows)}


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
    
    device = validate_batch_items(data.items, current_user, db)
    
    rows = [
        {
            "user_id": current_user.id,
            "device_id": device.id,
            "state": item.state,
            "start_ts": item.start_ts,
            "end_ts": item.end_ts,
            "duration_sec": item.duration_sec
        }
        for item in data.items
    ]

    db.bulk_insert_mappings(PresenceInterval, rows)
    refresh_daily_summaries(db, current_user.id, get_affected_dates(data.items))
    db.commit()
    
    return {"message": "Presence intervals ingested", "count": len(rows)}


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
    
    device = validate_batch_items(data.items, current_user, db)
    
    unique_domains = list({item.domain for item in data.items})
    domain_rules = db.query(DomainRule).filter(
        DomainRule.org_id == current_user.org_id,
        DomainRule.domain.in_(unique_domains)
    ).all()
    rules_by_domain: Dict[str, DomainRule] = {rule.domain: rule for rule in domain_rules}
    classifier = get_classifier(db)

    rows = []
    for item in data.items:
        rule = rules_by_domain.get(item.domain)
        if rule:
            if current_user.dept_id and rule.dept_overrides_json.get(str(current_user.dept_id)):
                category, label = rule.category, rule.dept_overrides_json[str(current_user.dept_id)]
            else:
                category, label = rule.category, rule.label
        else:
            category, label, _confidence = classifier.classify_domain(
                domain=item.domain,
                org_id=current_user.org_id,
                dept_id=current_user.dept_id,
            )
        rows.append({
            "user_id": current_user.id,
            "device_id": device.id,
            "browser": item.browser,
            "domain": item.domain,
            "start_ts": item.start_ts,
            "end_ts": item.end_ts,
            "duration_sec": item.duration_sec,
            "category": category,
            "label": label
        })

    db.bulk_insert_mappings(BrowserUsage, rows)
    refresh_daily_summaries(db, current_user.id, get_affected_dates(data.items))
    db.commit()
    
    return {"message": "Browser usage ingested", "count": len(rows)}
