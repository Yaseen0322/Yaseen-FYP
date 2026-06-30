"""
Operational runtime jobs for alert processing and Slack delivery.
"""
from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.alerts import AlertRule
from app.services.alert_processor import AlertProcessor
from app.services.slack_notifier import SlackNotifier


async def process_org_alerts(db: Session, org_id: int) -> Dict[str, int]:
    processor = AlertProcessor(db)
    created_records = processor.process_all_rules(org_id)

    if not created_records:
        db.rollback()
        return {"created_count": 0, "slack_sent": 0}

    db.commit()

    slack_notifier = SlackNotifier(db)
    slack_sent = 0
    for record in created_records:
        if not record["notify_manager"]:
            continue
        if await slack_notifier.send_alert_notification(record["alert"]):
            slack_sent += 1

    return {
        "created_count": len(created_records),
        "slack_sent": slack_sent,
    }


def get_alert_processing_org_ids(db: Session) -> List[int]:
    rows = db.query(AlertRule.org_id).filter(AlertRule.is_active == True).distinct().all()
    return [row[0] for row in rows]


async def process_all_alert_orgs(db: Session) -> List[Dict[str, int]]:
    results = []
    for org_id in get_alert_processing_org_ids(db):
        result = await process_org_alerts(db, org_id)
        result["org_id"] = org_id
        results.append(result)
    return results
