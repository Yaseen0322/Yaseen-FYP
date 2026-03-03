"""
Browser Usage and Domain Rule Schemas
"""
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class BrowserUsageCreate(BaseModel):
    device_id: int
    browser: str
    domain: str
    start_ts: datetime
    end_ts: datetime
    duration_sec: int


class BrowserUsageResponse(BaseModel):
    id: int
    user_id: int
    device_id: int
    browser: str
    domain: str
    start_ts: datetime
    end_ts: datetime
    duration_sec: int
    category: Optional[str]
    label: Optional[str]
    
    class Config:
        from_attributes = True


class BrowserUsageBatch(BaseModel):
    items: List[BrowserUsageCreate]


class DomainRuleCreate(BaseModel):
    domain: str
    category: str
    label: str  # productive, unproductive, neutral
    dept_overrides_json: Optional[Dict] = {}


class DomainRuleResponse(BaseModel):
    id: int
    org_id: int
    domain: str
    category: str
    label: str
    dept_overrides_json: Dict
    
    class Config:
        from_attributes = True
