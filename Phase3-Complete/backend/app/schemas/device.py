"""
Device Schemas
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DeviceRegister(BaseModel):
    machine_id: str
    hostname: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None


class DeviceResponse(BaseModel):
    id: int
    user_id: int
    machine_id: str
    hostname: Optional[str]
    os: Optional[str]
    app_version: Optional[str]
    is_active: bool
    last_seen: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
