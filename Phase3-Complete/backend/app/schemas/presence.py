"""
Presence Schemas
"""
from pydantic import BaseModel
from typing import List
from datetime import datetime


class PresenceIntervalCreate(BaseModel):
    device_id: int
    state: str  # present, absent, camera_off
    start_ts: datetime
    end_ts: datetime
    duration_sec: int


class PresenceIntervalResponse(BaseModel):
    id: int
    user_id: int
    device_id: int
    state: str
    start_ts: datetime
    end_ts: datetime
    duration_sec: int
    
    class Config:
        from_attributes = True


class PresenceIntervalBatch(BaseModel):
    items: List[PresenceIntervalCreate]
