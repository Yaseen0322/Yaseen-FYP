"""
Activity Schemas - App Usage and Idle Intervals
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AppUsageCreate(BaseModel):
    device_id: int
    app_name: str
    window_title: Optional[str] = None
    start_ts: datetime
    end_ts: datetime
    duration_sec: int


class AppUsageResponse(BaseModel):
    id: int
    user_id: int
    device_id: int
    app_name: str
    window_title: Optional[str]
    start_ts: datetime
    end_ts: datetime
    duration_sec: int
    
    class Config:
        from_attributes = True


class AppUsageBatch(BaseModel):
    items: List[AppUsageCreate]


class IdleIntervalCreate(BaseModel):
    device_id: int
    start_ts: datetime
    end_ts: datetime
    duration_sec: int


class IdleIntervalResponse(BaseModel):
    id: int
    user_id: int
    device_id: int
    start_ts: datetime
    end_ts: datetime
    duration_sec: int
    
    class Config:
        from_attributes = True


class IdleIntervalBatch(BaseModel):
    items: List[IdleIntervalCreate]
