"""End Device API routes"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.device_manager import device_manager


router = APIRouter()


class DeviceCreate(BaseModel):
    eui64: str
    border_router_id: int
    device_type: str = "sed"
    name: Optional[str] = None
    short_address: Optional[str] = None


class DeviceStatusUpdate(BaseModel):
    status: str
    rssi: Optional[int] = None
    link_quality: Optional[int] = None


@router.post("/")
async def register_device(device: DeviceCreate):
    """Register a new end device"""
    try:
        registered = await device_manager.register_device(
            eui64=device.eui64,
            border_router_id=device.border_router_id,
            device_type=device.device_type,
            name=device.name,
            short_address=device.short_address
        )
        return {
            "id": registered.id,
            "eui64": registered.eui64,
            "name": registered.name,
            "status": registered.status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk")
async def bulk_register_devices(devices: List[Dict[str, Any]]):
    """Bulk register devices"""
    try:
        registered = await device_manager.bulk_register_devices(devices)
        return {
            "count": len(registered),
            "devices": [{"id": d.id, "eui64": d.eui64} for d in registered]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_devices(
    border_router_id: Optional[int] = None,
    status: Optional[str] = None,
    device_type: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0
):
    """List devices with pagination"""
    result = await device_manager.list_devices(
        border_router_id=border_router_id,
        status=status,
        device_type=device_type,
        limit=limit,
        offset=offset
    )

    return {
        "devices": [
            {
                "id": d.id,
                "eui64": d.eui64,
                "name": d.name,
                "device_type": d.device_type,
                "status": d.status,
                "rssi": d.rssi,
                "border_router_id": d.border_router_id,
                "last_seen": d.last_seen.isoformat() if d.last_seen else None
            }
            for d in result["devices"]
        ],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
        "has_more": result["has_more"]
    }


@router.get("/search")
async def search_devices(q: str, limit: int = 100):
    """Search devices by name or EUI64"""
    devices = await device_manager.search_devices(q, limit)
    return [
        {
            "id": d.id,
            "eui64": d.eui64,
            "name": d.name,
            "status": d.status
        }
        for d in devices
    ]


@router.get("/statistics")
async def get_device_statistics(border_router_id: Optional[int] = None):
    """Get device statistics"""
    stats = await device_manager.get_device_statistics(border_router_id)
    return stats


@router.get("/{device_id}")
async def get_device(device_id: int):
    """Get device details"""
    device = await device_manager.get_device(device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "id": device.id,
        "eui64": device.eui64,
        "name": device.name,
        "device_type": device.device_type,
        "status": device.status,
        "rssi": device.rssi,
        "link_quality": device.link_quality,
        "border_router_id": device.border_router_id,
        "firmware_version": device.firmware_version,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "metadata": device.metadata
    }


@router.put("/{device_id}/status")
async def update_device_status(device_id: int, update: DeviceStatusUpdate):
    """Update device status"""
    try:
        await device_manager.update_device_status(
            device_id=device_id,
            status=update.status,
            rssi=update.rssi,
            link_quality=update.link_quality
        )
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/router/{border_router_id}/tree")
async def get_device_tree(border_router_id: int):
    """Get hierarchical device tree"""
    try:
        tree = await device_manager.get_device_tree(border_router_id)
        return tree
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/detect-stale")
async def detect_stale_devices(threshold_minutes: int = 60):
    """Detect and mark stale devices as offline"""
    stale = await device_manager.detect_stale_devices(threshold_minutes)
    return {
        "count": len(stale),
        "devices": [{"id": d.id, "eui64": d.eui64, "name": d.name} for d in stale]
    }


@router.delete("/{device_id}")
async def delete_device(device_id: int):
    """Delete a device"""
    try:
        await device_manager.delete_device(device_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
