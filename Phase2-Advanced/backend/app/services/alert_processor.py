"""
Alert Processor Service - Phase 2
Background job to check alert rules and generate alerts
"""
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.alerts import Alert, AlertRule, AlertType
from app.models.user import User
from app.models.activity import IdleInterval
from app.models.presence import PresenceInterval
from app.models.browser_usage import BrowserUsage


class AlertProcessor:
    def __init__(self, db: Session):
        self.db = db
    
    def process_all_rules(self, org_id: int):
        """Process all active rules for an organization"""
        rules = self.db.query(AlertRule).filter(
            AlertRule.org_id == org_id,
            AlertRule.is_active == True
        ).all()
        
        for rule in rules:
            self.process_rule(rule)
    
    def process_rule(self, rule: AlertRule):
        """Process a single alert rule"""
        if rule.alert_type == AlertType.EXCESSIVE_IDLE.value:
            self._check_excessive_idle(rule)
        elif rule.alert_type == AlertType.CAMERA_OFF_LONG.value:
            self._check_camera_off(rule)
        elif rule.alert_type == AlertType.LOW_PRODUCTIVITY.value:
            self._check_low_productivity(rule)
    
    def _check_excessive_idle(self, rule: AlertRule):
        """Check for excessive idle time"""
        threshold_sec = rule.config_json.get("threshold_seconds", 7200)  # 2 hours default
        today = date.today()
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.now()
        
        # Get all employees in org
        employees = self.db.query(User).filter(
            User.org_id == rule.org_id,
            User.role == "employee",
            User.is_active == True
        ).all()
        
        for emp in employees:
            # Check total idle today
            total_idle = self.db.query(func.sum(IdleInterval.duration_sec)).filter(
                IdleInterval.user_id == emp.id,
                IdleInterval.start_ts >= start_dt,
                IdleInterval.end_ts <= end_dt
            ).scalar() or 0
            
            if total_idle >= threshold_sec:
                # Check if alert already exists today
                existing = self.db.query(Alert).filter(
                    Alert.user_id == emp.id,
                    Alert.alert_type == AlertType.EXCESSIVE_IDLE.value,
                    func.date(Alert.triggered_at) == today
                ).first()
                
                if not existing:
                    alert = Alert(
                        org_id=rule.org_id,
                        user_id=emp.id,
                        rule_id=rule.id,
                        alert_type=AlertType.EXCESSIVE_IDLE.value,
                        severity=rule.severity,
                        title=f"Excessive idle time detected",
                        message=f"{emp.name} has been idle for {total_idle // 3600}h {(total_idle % 3600) // 60}m today.",
                        context_json={
                            "idle_duration_sec": total_idle,
                            "threshold_sec": threshold_sec,
                            "date": today.isoformat()
                        }
                    )
                    self.db.add(alert)
        
        self.db.commit()
    
    def _check_camera_off(self, rule: AlertRule):
        """Check for camera off too long"""
        threshold_sec = rule.config_json.get("threshold_seconds", 3600)  # 1 hour default
        today = date.today()
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.now()
        
        employees = self.db.query(User).filter(
            User.org_id == rule.org_id,
            User.role == "employee",
            User.is_active == True
        ).all()
        
        for emp in employees:
            # Check camera off time
            camera_off = self.db.query(func.sum(PresenceInterval.duration_sec)).filter(
                PresenceInterval.user_id == emp.id,
                PresenceInterval.state == "camera_off",
                PresenceInterval.start_ts >= start_dt,
                PresenceInterval.end_ts <= end_dt
            ).scalar() or 0
            
            if camera_off >= threshold_sec:
                existing = self.db.query(Alert).filter(
                    Alert.user_id == emp.id,
                    Alert.alert_type == AlertType.CAMERA_OFF_LONG.value,
                    func.date(Alert.triggered_at) == today
                ).first()
                
                if not existing:
                    alert = Alert(
                        org_id=rule.org_id,
                        user_id=emp.id,
                        rule_id=rule.id,
                        alert_type=AlertType.CAMERA_OFF_LONG.value,
                        severity=rule.severity,
                        title=f"Camera off for extended period",
                        message=f"{emp.name}'s camera has been off for {camera_off // 3600}h {(camera_off % 3600) // 60}m today.",
                        context_json={
                            "camera_off_sec": camera_off,
                            "threshold_sec": threshold_sec,
                            "date": today.isoformat()
                        }
                    )
                    self.db.add(alert)
        
        self.db.commit()
    
    def _check_low_productivity(self, rule: AlertRule):
        """Check for low productivity"""
        threshold_percent = rule.config_json.get("threshold_percent", 30)  # 30% default
        min_browser_time = rule.config_json.get("min_browser_time_sec", 1800)  # 30 min minimum
        
        today = date.today()
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.now()
        
        employees = self.db.query(User).filter(
            User.org_id == rule.org_id,
            User.role == "employee",
            User.is_active == True
        ).all()
        
        for emp in employees:
            # Get browser usage
            productive = self.db.query(func.sum(BrowserUsage.duration_sec)).filter(
                BrowserUsage.user_id == emp.id,
                BrowserUsage.label == "productive",
                BrowserUsage.start_ts >= start_dt,
                BrowserUsage.end_ts <= end_dt
            ).scalar() or 0
            
            total_browser = self.db.query(func.sum(BrowserUsage.duration_sec)).filter(
                BrowserUsage.user_id == emp.id,
                BrowserUsage.start_ts >= start_dt,
                BrowserUsage.end_ts <= end_dt
            ).scalar() or 0
            
            if total_browser < min_browser_time:
                continue  # Not enough data
            
            productivity = (productive / total_browser * 100) if total_browser > 0 else 0
            
            if productivity < threshold_percent:
                existing = self.db.query(Alert).filter(
                    Alert.user_id == emp.id,
                    Alert.alert_type == AlertType.LOW_PRODUCTIVITY.value,
                    func.date(Alert.triggered_at) == today
                ).first()
                
                if not existing:
                    alert = Alert(
                        org_id=rule.org_id,
                        user_id=emp.id,
                        rule_id=rule.id,
                        alert_type=AlertType.LOW_PRODUCTIVITY.value,
                        severity=rule.severity,
                        title=f"Low productivity detected",
                        message=f"{emp.name}'s productivity is at {productivity:.1f}% (threshold: {threshold_percent}%).",
                        context_json={
                            "productivity_percent": round(productivity, 1),
                            "threshold_percent": threshold_percent,
                            "productive_sec": productive,
                            "total_browser_sec": total_browser,
                            "date": today.isoformat()
                        }
                    )
                    self.db.add(alert)
        
        self.db.commit()


def run_alert_processor(db: Session, org_id: int):
    """Run the alert processor for an organization"""
    processor = AlertProcessor(db)
    processor.process_all_rules(org_id)
