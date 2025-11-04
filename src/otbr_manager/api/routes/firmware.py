"""Firmware API routes"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.firmware import firmware_manager


router = APIRouter()


class FirmwareCreate(BaseModel):
    version: str
    file_path: str
    device_types: List[str]
    description: Optional[str] = None
    release_notes: Optional[str] = None


class UpdateSchedule(BaseModel):
    device_id: int
    firmware_version_id: int


class BulkUpdateSchedule(BaseModel):
    device_ids: List[int]
    firmware_version_id: int


@router.post("/versions")
async def register_firmware(firmware: FirmwareCreate):
    """Register a new firmware version"""
    try:
        registered = await firmware_manager.register_firmware(
            version=firmware.version,
            file_path=firmware.file_path,
            device_types=firmware.device_types,
            description=firmware.description,
            release_notes=firmware.release_notes
        )
        return {
            "id": registered.id,
            "version": registered.version,
            "file_hash": registered.file_hash
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/versions")
async def list_firmware_versions(active_only: bool = True):
    """List all firmware versions"""
    versions = await firmware_manager.list_firmware_versions(active_only)
    return [
        {
            "id": v.id,
            "version": v.version,
            "device_types": v.device_types,
            "file_size": v.file_size,
            "description": v.description,
            "is_active": v.is_active,
            "created_at": v.created_at.isoformat()
        }
        for v in versions
    ]


@router.get("/versions/{firmware_id}")
async def get_firmware_version(firmware_id: int):
    """Get firmware version details"""
    firmware = await firmware_manager.get_firmware_version(firmware_id)
    if not firmware:
        raise HTTPException(status_code=404, detail="Firmware version not found")

    return {
        "id": firmware.id,
        "version": firmware.version,
        "file_path": firmware.file_path,
        "file_hash": firmware.file_hash,
        "file_size": firmware.file_size,
        "device_types": firmware.device_types,
        "description": firmware.description,
        "release_notes": firmware.release_notes,
        "is_active": firmware.is_active
    }


@router.post("/updates/schedule")
async def schedule_update(schedule: UpdateSchedule):
    """Schedule a firmware update"""
    try:
        update = await firmware_manager.schedule_update(
            device_id=schedule.device_id,
            firmware_version_id=schedule.firmware_version_id
        )
        return {
            "update_id": update.id,
            "status": update.status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/updates/schedule-bulk")
async def schedule_bulk_updates(schedule: BulkUpdateSchedule):
    """Schedule firmware updates for multiple devices"""
    try:
        updates = await firmware_manager.schedule_bulk_updates(
            device_ids=schedule.device_ids,
            firmware_version_id=schedule.firmware_version_id
        )
        return {
            "count": len(updates),
            "update_ids": [u.id for u in updates]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/updates/{update_id}/start")
async def start_update(update_id: int):
    """Start a firmware update"""
    try:
        await firmware_manager.start_update(update_id)
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/updates/{update_id}/cancel")
async def cancel_update(update_id: int):
    """Cancel a firmware update"""
    try:
        await firmware_manager.cancel_update(update_id)
        return {"status": "cancelled"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/updates/{update_id}/retry")
async def retry_update(update_id: int):
    """Retry a failed firmware update"""
    try:
        await firmware_manager.retry_failed_update(update_id)
        return {"status": "retrying"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/updates/{update_id}/status")
async def get_update_status(update_id: int):
    """Get firmware update status"""
    try:
        status = await firmware_manager.get_update_status(update_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/updates/device/{device_id}")
async def get_device_updates(device_id: int):
    """Get all firmware updates for a device"""
    updates = await firmware_manager.get_device_updates(device_id)
    return [
        {
            "id": u.id,
            "firmware_version": u.firmware_version.version,
            "status": u.status,
            "progress": u.progress,
            "started_at": u.started_at.isoformat() if u.started_at else None,
            "completed_at": u.completed_at.isoformat() if u.completed_at else None
        }
        for u in updates
    ]


@router.get("/updates/statistics")
async def get_update_statistics():
    """Get firmware update statistics"""
    stats = await firmware_manager.get_update_statistics()
    return stats
