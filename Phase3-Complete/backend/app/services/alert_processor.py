"""
Alert Processor Service
Evaluates configured alert rules against corrected daily summaries.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dates import utc_today
from app.models.alerts import Alert, AlertRule, AlertType
from app.models.daily_summary import DailySummary
from app.models.user import User


class AlertProcessor:
    def __init__(self, db: Session):
        self.db = db

    def process_all_rules(self, org_id: int, target_date: date | None = None) -> List[Dict[str, Any]]:
        """
        Evaluate all active rules for an organization and stage new alerts.
        The caller is responsible for committing the session.
        """
        evaluation_date = target_date or utc_today()
        rules = self.db.query(AlertRule).filter(
            AlertRule.org_id == org_id,
            AlertRule.is_active == True,
        ).all()

        created_records: List[Dict[str, Any]] = []
        for rule in rules:
            created_records.extend(self.process_rule(rule, evaluation_date))
        return created_records

    def process_rule(self, rule: AlertRule, target_date: date | None = None) -> List[Dict[str, Any]]:
        evaluation_date = target_date or utc_today()
        employees = self._get_employee_daily_metrics(rule.org_id, evaluation_date)
        existing_user_ids = self._get_existing_alert_user_ids(rule.org_id, rule.alert_type, evaluation_date)
        created_records: List[Dict[str, Any]] = []

        for employee in employees:
            if employee["user_id"] in existing_user_ids:
                continue

            alert_payload = self._build_alert_payload(rule, employee, evaluation_date)
            if not alert_payload:
                continue

            dedupe_key = self._build_dedupe_key(
                org_id=rule.org_id,
                user_id=employee["user_id"],
                alert_type=rule.alert_type,
                target_date=evaluation_date,
            )

            alert = Alert(
                org_id=rule.org_id,
                user_id=employee["user_id"],
                rule_id=rule.id,
                alert_type=rule.alert_type,
                severity=rule.severity,
                title=alert_payload["title"],
                message=alert_payload["message"],
                context_json=alert_payload["context_json"],
                dedupe_key=dedupe_key,
            )
            try:
                with self.db.begin_nested():
                    self.db.add(alert)
                    self.db.flush()
            except IntegrityError:
                continue

            existing_user_ids.add(employee["user_id"])
            created_records.append(
                {
                    "alert": alert,
                    "notify_manager": rule.notify_manager,
                    "notify_employee": rule.notify_employee,
                }
            )

        return created_records

    def _get_employee_daily_metrics(self, org_id: int, target_date: date) -> List[Dict[str, Any]]:
        rows = self.db.query(
            User.id,
            User.name,
            DailySummary.focus_sec,
            DailySummary.idle_sec,
            DailySummary.present_sec,
            DailySummary.camera_off_sec,
            DailySummary.productive_sec,
            DailySummary.unproductive_sec,
            DailySummary.neutral_sec,
        ).outerjoin(
            DailySummary,
            and_(DailySummary.user_id == User.id, DailySummary.date == target_date),
        ).filter(
            User.org_id == org_id,
            User.role == "employee",
            User.is_active == True,
        ).all()

        return [
            {
                "user_id": row[0],
                "name": row[1],
                "focus_sec": row[2] or 0,
                "idle_sec": row[3] or 0,
                "present_sec": row[4] or 0,
                "camera_off_sec": row[5] or 0,
                "productive_sec": row[6] or 0,
                "unproductive_sec": row[7] or 0,
                "neutral_sec": row[8] or 0,
            }
            for row in rows
        ]

    def _get_existing_alert_user_ids(self, org_id: int, alert_type: str, target_date: date) -> set[int]:
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        rows = self.db.query(Alert.user_id).filter(
            Alert.org_id == org_id,
            Alert.alert_type == alert_type,
            Alert.triggered_at >= day_start,
            Alert.triggered_at < day_end,
        ).all()
        return {row[0] for row in rows}

    def _build_alert_payload(self, rule: AlertRule, employee: Dict[str, Any], target_date: date) -> Dict[str, Any] | None:
        if rule.alert_type == AlertType.EXCESSIVE_IDLE.value:
            return self._build_excessive_idle_alert(rule, employee, target_date)
        if rule.alert_type == AlertType.CAMERA_OFF_LONG.value:
            return self._build_camera_off_alert(rule, employee, target_date)
        if rule.alert_type == AlertType.LOW_PRODUCTIVITY.value:
            return self._build_low_productivity_alert(rule, employee, target_date)
        return None

    def _build_excessive_idle_alert(self, rule: AlertRule, employee: Dict[str, Any], target_date: date) -> Dict[str, Any] | None:
        threshold_sec = int(rule.config_json.get("threshold_seconds", 7200))
        total_idle = employee["idle_sec"]
        if total_idle < threshold_sec:
            return None

        return {
            "title": "Excessive idle time detected",
            "message": (
                f"{employee['name']} has been idle for "
                f"{total_idle // 3600}h {(total_idle % 3600) // 60}m today."
            ),
            "context_json": {
                "idle_duration_sec": total_idle,
                "threshold_sec": threshold_sec,
                "date": target_date.isoformat(),
            },
        }

    def _build_camera_off_alert(self, rule: AlertRule, employee: Dict[str, Any], target_date: date) -> Dict[str, Any] | None:
        threshold_sec = int(rule.config_json.get("threshold_seconds", 3600))
        camera_off = employee["camera_off_sec"]
        if camera_off < threshold_sec:
            return None

        return {
            "title": "Camera off for extended period",
            "message": (
                f"{employee['name']}'s camera has been off for "
                f"{camera_off // 3600}h {(camera_off % 3600) // 60}m today."
            ),
            "context_json": {
                "camera_off_sec": camera_off,
                "threshold_sec": threshold_sec,
                "date": target_date.isoformat(),
            },
        }

    def _build_low_productivity_alert(self, rule: AlertRule, employee: Dict[str, Any], target_date: date) -> Dict[str, Any] | None:
        threshold_percent = float(rule.config_json.get("threshold_percent", 30))
        min_browser_time = int(rule.config_json.get("min_browser_time_sec", 1800))
        total_browser = (
            employee["productive_sec"] +
            employee["unproductive_sec"] +
            employee["neutral_sec"]
        )

        if total_browser < min_browser_time:
            return None

        productivity = (employee["productive_sec"] / total_browser * 100) if total_browser else 0.0
        if productivity >= threshold_percent:
            return None

        return {
            "title": "Low productivity detected",
            "message": (
                f"{employee['name']}'s productivity is at {productivity:.1f}% "
                f"(threshold: {threshold_percent:.1f}%)."
            ),
            "context_json": {
                "productivity_percent": round(productivity, 1),
                "threshold_percent": threshold_percent,
                "productive_sec": employee["productive_sec"],
                "total_browser_sec": total_browser,
                "date": target_date.isoformat(),
            },
        }

    def _build_dedupe_key(self, org_id: int, user_id: int, alert_type: str, target_date: date) -> str:
        return f"{org_id}:{user_id}:{alert_type}:{target_date.isoformat()}"


def run_alert_processor(db: Session, org_id: int, target_date: date | None = None) -> List[Dict[str, Any]]:
    """Run the alert processor for an organization."""
    processor = AlertProcessor(db)
    return processor.process_all_rules(org_id, target_date=target_date)
