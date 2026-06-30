"""
Slack Notifier Service - Phase 3
Sends notifications to Slack
"""
import httpx
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.crypto import decrypt_json_payload
from app.models.integrations import Integration, IntegrationType
from app.models.alerts import Alert


class SlackNotifier:
    def __init__(self, db: Session):
        self.db = db
    
    def get_slack_config(self, org_id: int) -> Optional[Dict[str, Any]]:
        """Get Slack integration config for org"""
        integration = self.db.query(Integration).filter(
            Integration.org_id == org_id,
            Integration.integration_type == IntegrationType.SLACK.value,
            Integration.is_active == True
        ).first()
        
        if integration and integration.is_configured:
            return decrypt_json_payload(integration.config_json)
        return None
    
    async def send_alert_notification(self, alert: Alert):
        """Send alert to Slack"""
        config = self.get_slack_config(alert.org_id)
        if not config:
            return False
        
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return False
        
        # Format message
        severity_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🔵"
        }
        
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{severity_emoji.get(alert.severity, '⚪')} Activity Tracker Alert"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Type:*\n{alert.alert_type.replace('_', ' ').title()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{alert.severity.title()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{alert.title}*\n{alert.message}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Triggered at {alert.triggered_at.strftime('%Y-%m-%d %H:%M UTC')}"
                        }
                    ]
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=message)
                return response.status_code == 200
        except Exception as e:
            print(f"Slack notification error: {e}")
            return False
    
    async def send_daily_summary(self, org_id: int, summary: Dict[str, Any]):
        """Send daily summary to Slack"""
        config = self.get_slack_config(org_id)
        if not config:
            return False
        
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return False
        
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Daily Activity Summary"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Date:*\n{summary.get('date', 'Today')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Employees:*\n{summary.get('employee_count', 0)}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Focus Time:*\n{self._format_time(summary.get('total_focus_sec', 0))}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Avg Focus/Employee:*\n{self._format_time(summary.get('avg_focus_sec', 0))}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Present:*\n{self._format_time(summary.get('total_present_sec', 0))}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Alerts Today:*\n{summary.get('alert_count', 0)}"
                        }
                    ]
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=message)
                return response.status_code == 200
        except Exception as e:
            print(f"Slack summary error: {e}")
            return False
    
    def _format_time(self, seconds: int) -> str:
        if not seconds:
            return "0h"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


async def notify_alert_to_slack(db: Session, alert: Alert):
    """Helper function to send alert notification"""
    notifier = SlackNotifier(db)
    await notifier.send_alert_notification(alert)
