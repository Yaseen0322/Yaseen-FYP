"""
Alerts API Routes - Phase 2
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user, get_current_manager
from app.models.user import User
from app.models.alerts import Alert, AlertRule, AlertType, AlertSeverity

router = APIRouter()


# Pydantic schemas for alerts
from pydantic import BaseModel
from typing import Dict, Any


class AlertRuleCreate(BaseModel):
    name: str
    alert_type: str
    severity: str = "medium"
    config_json: Dict[str, Any] = {}
    notify_employee: bool = False
    notify_manager: bool = True


class AlertRuleResponse(BaseModel):
    id: int
    org_id: int
    name: str
    alert_type: str
    severity: str
    is_active: bool
    config_json: Dict[str, Any]
    notify_employee: bool
    notify_manager: bool
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    user_id: int
    alert_type: str
    severity: str
    title: str
    message: Optional[str]
    context_json: Dict[str, Any]
    is_read: bool
    is_acknowledged: bool
    triggered_at: datetime
    
    class Config:
        from_attributes = True


# Alert Rules CRUD
@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """List all alert rules for organization"""
    rules = db.query(AlertRule).filter(
        AlertRule.org_id == current_user.org_id
    ).all()
    return rules


@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Create new alert rule"""
    rule = AlertRule(
        org_id=current_user.org_id,
        name=rule_data.name,
        alert_type=rule_data.alert_type,
        severity=rule_data.severity,
        config_json=rule_data.config_json,
        notify_employee=rule_data.notify_employee,
        notify_manager=rule_data.notify_manager,
        is_active=True
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}")
async def toggle_alert_rule(
    rule_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Toggle alert rule active status"""
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id,
        AlertRule.org_id == current_user.org_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule.is_active = is_active
    db.commit()
    return {"message": "Rule updated", "is_active": is_active}


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Delete alert rule"""
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id,
        AlertRule.org_id == current_user.org_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    return {"message": "Rule deleted"}


# Alerts
@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    user_id: Optional[int] = None,
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    unread_only: bool = False,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """List alerts for organization"""
    query = db.query(Alert).filter(Alert.org_id == current_user.org_id)
    
    if user_id:
        query = query.filter(Alert.user_id == user_id)
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    if severity:
        query = query.filter(Alert.severity == severity)
    if unread_only:
        query = query.filter(Alert.is_read == False)
    
    alerts = query.order_by(Alert.triggered_at.desc()).limit(limit).all()
    return alerts


@router.get("/my", response_model=List[AlertResponse])
async def list_my_alerts(
    unread_only: bool = False,
    limit: int = Query(default=20, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List alerts for current user"""
    query = db.query(Alert).filter(Alert.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Alert.is_read == False)
    
    alerts = query.order_by(Alert.triggered_at.desc()).limit(limit).all()
    return alerts


@router.post("/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark alert as read"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Verify access
    if alert.user_id != current_user.id and current_user.role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    alert.is_read = True
    db.commit()
    return {"message": "Alert marked as read"}


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Acknowledge an alert (manager only)"""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.org_id == current_user.org_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"message": "Alert acknowledged"}


@router.get("/stats")
async def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """Get alert statistics"""
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # Total alerts
    total = db.query(func.count(Alert.id)).filter(
        Alert.org_id == current_user.org_id
    ).scalar()
    
    # Unread alerts
    unread = db.query(func.count(Alert.id)).filter(
        Alert.org_id == current_user.org_id,
        Alert.is_read == False
    ).scalar()
    
    # Alerts by severity
    by_severity = db.query(
        Alert.severity,
        func.count(Alert.id)
    ).filter(
        Alert.org_id == current_user.org_id,
        func.date(Alert.triggered_at) >= week_ago
    ).group_by(Alert.severity).all()
    
    # Alerts by type
    by_type = db.query(
        Alert.alert_type,
        func.count(Alert.id)
    ).filter(
        Alert.org_id == current_user.org_id,
        func.date(Alert.triggered_at) >= week_ago
    ).group_by(Alert.alert_type).all()
    
    return {
        "total": total,
        "unread": unread,
        "by_severity": {s: c for s, c in by_severity},
        "by_type": {t: c for t, c in by_type}
    }
