"""
Device Management API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.device import Device
from app.schemas.device import DeviceRegister, DeviceResponse

router = APIRouter()


@router.post("/register", response_model=DeviceResponse)
async def register_device(
    device_data: DeviceRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Register or update a device for the current user
    """
    # Check if device already exists
    device = db.query(Device).filter(
        Device.machine_id == device_data.machine_id
    ).first()
    
    if device:
        # Update existing device
        device.user_id = current_user.id
        device.hostname = device_data.hostname
        device.os = device_data.os
        device.os_version = device_data.os_version
        device.app_version = device_data.app_version
        device.last_seen = datetime.utcnow()
        device.is_active = True
    else:
        # Create new device
        device = Device(
            user_id=current_user.id,
            machine_id=device_data.machine_id,
            hostname=device_data.hostname,
            os=device_data.os,
            os_version=device_data.os_version,
            app_version=device_data.app_version,
            last_seen=datetime.utcnow(),
            is_active=True
        )
        db.add(device)
    
    db.commit()
    db.refresh(device)
    
    return DeviceResponse.model_validate(device)


@router.get("/", response_model=List[DeviceResponse])
async def list_my_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all devices for current user
    """
    devices = db.query(Device).filter(
        Device.user_id == current_user.id
    ).all()
    
    return [DeviceResponse.model_validate(d) for d in devices]


@router.post("/heartbeat/{device_id}")
async def device_heartbeat(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update device last seen timestamp
    """
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.user_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.last_seen = datetime.utcnow()
    db.commit()
    
    return {"message": "Heartbeat received", "timestamp": datetime.utcnow()}


@router.delete("/{device_id}")
async def deactivate_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deactivate a device
    """
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.user_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.is_active = False
    db.commit()
    
    return {"message": "Device deactivated"}
