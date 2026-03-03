"""
Report Schemas
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class DailySummaryResponse(BaseModel):
    id: int
    user_id: int
    date: date
    focus_sec: int
    idle_sec: int
    present_sec: int
    absent_sec: int
    camera_off_sec: int
    productive_sec: int
    unproductive_sec: int
    neutral_sec: int
    top_apps_json: List[Dict[str, Any]]
    top_domains_json: List[Dict[str, Any]]
    first_activity: Optional[datetime]
    last_activity: Optional[datetime]
    
    class Config:
        from_attributes = True


class TimelineBlock(BaseModel):
    type: str  # app_usage, idle, present, absent, camera_off
    start_ts: datetime
    end_ts: datetime
    duration_sec: int
    details: Optional[Dict[str, Any]] = None


class TimelineResponse(BaseModel):
    date: date
    blocks: List[TimelineBlock]


class AppUsageSummary(BaseModel):
    app_name: str
    total_duration_sec: int
    percentage: float


class DomainUsageSummary(BaseModel):
    domain: str
    category: Optional[str]
    label: Optional[str]
    total_duration_sec: int
    percentage: float


class WeeklySummary(BaseModel):
    week_start: date
    week_end: date
    daily_summaries: List[DailySummaryResponse]
    total_focus_sec: int
    total_idle_sec: int
    total_present_sec: int
    avg_daily_focus_sec: float
    avg_daily_present_sec: float
    top_apps: List[AppUsageSummary]
    top_domains: List[DomainUsageSummary]
