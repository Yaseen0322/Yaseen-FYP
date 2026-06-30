"""
Jira Integration Service - Phase 3
Supports connectivity checks and future export hooks.
Automatic sync is not enabled in this release candidate.
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.core.crypto import decrypt_json_payload
from app.models.integrations import Integration, IntegrationType
from app.models.user import User


class JiraIntegration:
    def __init__(self, db: Session):
        self.db = db
    
    def get_jira_config(self, org_id: int) -> Optional[Dict[str, Any]]:
        """Get Jira integration config for org"""
        integration = self.db.query(Integration).filter(
            Integration.org_id == org_id,
            Integration.integration_type == IntegrationType.JIRA.value,
            Integration.is_active == True
        ).first()
        
        if integration and integration.is_configured:
            return decrypt_json_payload(integration.config_json)
        return None
    
    async def get_user_issues(
        self,
        org_id: int,
        user_email: str,
        days: int = 7
    ) -> Optional[List[Dict[str, Any]]]:
        """Get issues assigned to user in the last N days"""
        config = self.get_jira_config(org_id)
        if not config:
            return None
        
        api_url = config.get("api_url")
        api_token = config.get("api_token")
        email = config.get("email")
        
        if not all([api_url, api_token, email]):
            return None
        
        # JQL query for user's issues
        start_date = (date.today() - timedelta(days=days)).isoformat()
        jql = f'assignee = "{user_email}" AND updated >= "{start_date}"'
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{api_url}/rest/api/3/search",
                    params={
                        "jql": jql,
                        "fields": "summary,status,timetracking,worklog"
                    },
                    auth=(email, api_token)
                )
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                issues = []
                
                for issue in data.get("issues", []):
                    fields = issue.get("fields", {})
                    issues.append({
                        "key": issue.get("key"),
                        "summary": fields.get("summary"),
                        "status": fields.get("status", {}).get("name"),
                        "time_spent_seconds": fields.get("timetracking", {}).get("timeSpentSeconds", 0)
                    })
                
                return issues
        except Exception as e:
            print(f"Jira API error: {e}")
            return None
    
    async def log_work(
        self,
        org_id: int,
        issue_key: str,
        time_spent_seconds: int,
        comment: Optional[str] = None
    ) -> bool:
        """Log work time on a Jira issue"""
        config = self.get_jira_config(org_id)
        if not config:
            return False
        
        api_url = config.get("api_url")
        api_token = config.get("api_token")
        email = config.get("email")
        
        if not all([api_url, api_token, email]):
            return False
        
        # Convert seconds to Jira format
        worklog = {
            "timeSpentSeconds": time_spent_seconds,
            "started": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        }
        
        if comment:
            worklog["comment"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": comment}
                        ]
                    }
                ]
            }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_url}/rest/api/3/issue/{issue_key}/worklog",
                    json=worklog,
                    auth=(email, api_token)
                )
                
                return response.status_code in [200, 201]
        except Exception as e:
            print(f"Jira worklog error: {e}")
            return False
    
    async def get_project_issues(
        self,
        org_id: int,
        project_key: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get all issues for a project"""
        config = self.get_jira_config(org_id)
        if not config:
            return None
        
        api_url = config.get("api_url")
        api_token = config.get("api_token")
        email = config.get("email")
        
        if not all([api_url, api_token, email]):
            return None
        
        jql = f'project = "{project_key}"'
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{api_url}/rest/api/3/search",
                    params={
                        "jql": jql,
                        "maxResults": 100,
                        "fields": "summary,status,assignee"
                    },
                    auth=(email, api_token)
                )
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                issues = []
                
                for issue in data.get("issues", []):
                    fields = issue.get("fields", {})
                    assignee = fields.get("assignee")
                    issues.append({
                        "key": issue.get("key"),
                        "summary": fields.get("summary"),
                        "status": fields.get("status", {}).get("name"),
                        "assignee_email": assignee.get("emailAddress") if assignee else None
                    })
                
                return issues
        except Exception as e:
            print(f"Jira API error: {e}")
            return None


async def sync_jira_data(db: Session, org_id: int):
    """Reserved hook for future Jira sync jobs."""
    jira = JiraIntegration(db)
    
    # Get all employees
    employees = db.query(User).filter(
        User.org_id == org_id,
        User.role == "employee",
        User.is_active == True
    ).all()
    
    for emp in employees:
        issues = await jira.get_user_issues(org_id, emp.email)
        if issues:
            # Store issues data (could be added to user profile or separate table)
            print(f"Synced {len(issues)} issues for {emp.email}")
