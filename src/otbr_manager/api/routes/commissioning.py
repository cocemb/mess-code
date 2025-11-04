"""Commissioner API routes for device joining"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ...core.commissioner import commissioner_service
from ...core.otbr_agent import otbr_agent


router = APIRouter()


class CommissionerStart(BaseModel):
    border_router_id: int


class CommissionDeviceRequest(BaseModel):
    border_router_id: int
    pskd: str
    eui64: Optional[str] = None
    device_name: Optional[str] = None
    device_type: str = "sed"
    timeout: int = 120


class BulkCommissionRequest(BaseModel):
    border_router_id: int
    devices: List[Dict[str, Any]]
    batch_timeout: int = 300


@router.post("/start")
async def start_commissioner(req: CommissionerStart):
    """Start Thread Commissioner"""
    try:
        success = await commissioner_service.start(req.border_router_id)
        if success:
            return {"status": "commissioner_active"}
        else:
            raise HTTPException(status_code=500, detail="Failed to start commissioner")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_commissioner():
    """Stop Thread Commissioner"""
    try:
        await commissioner_service.stop()
        return {"status": "commissioner_stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_commissioner_status():
    """Get commissioner status"""
    return {
        "active": commissioner_service.commissioner_active,
        "active_sessions": await commissioner_service.get_active_sessions()
    }


@router.post("/commission")
async def commission_device(req: CommissionDeviceRequest, background_tasks: BackgroundTasks):
    """
    Commission a new device to join the Thread network

    The device must be in commissioning mode with the provided PSKd
    """
    try:
        device = await commissioner_service.commission_device(
            border_router_id=req.border_router_id,
            pskd=req.pskd,
            eui64=req.eui64,
            device_name=req.device_name,
            device_type=req.device_type,
            timeout=req.timeout
        )

        if device:
            return {
                "status": "commissioned",
                "device": {
                    "id": device.id,
                    "eui64": device.eui64,
                    "name": device.name,
                    "rloc16": device.rloc16
                }
            }
        else:
            raise HTTPException(
                status_code=408,
                detail="Device commissioning timeout - device did not join"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commission/bulk")
async def commission_multiple_devices(req: BulkCommissionRequest):
    """Commission multiple devices in batch"""
    try:
        devices = await commissioner_service.commission_multiple_devices(
            border_router_id=req.border_router_id,
            devices=req.devices,
            batch_timeout=req.batch_timeout
        )

        return {
            "status": "completed",
            "total": len(req.devices),
            "successful": len(devices),
            "devices": [
                {
                    "id": d.id,
                    "eui64": d.eui64,
                    "name": d.name
                }
                for d in devices
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_active_sessions():
    """Get list of active commissioning sessions"""
    sessions = await commissioner_service.get_active_sessions()
    return {"sessions": sessions}


@router.delete("/sessions/{eui64}")
async def cancel_session(eui64: str):
    """Cancel a commissioning session"""
    success = await commissioner_service.cancel_session(eui64)
    if success:
        return {"status": "cancelled"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


# Network topology queries via ot-ctl

@router.get("/network/children")
async def get_child_table():
    """Get child device table from OTBR"""
    try:
        children = await otbr_agent.get_child_table()
        return {"children": children}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network/neighbors")
async def get_neighbor_table():
    """Get neighbor router table"""
    try:
        neighbors = await otbr_agent.get_neighbor_table()
        return {"neighbors": neighbors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network/routers")
async def get_router_table():
    """Get router table"""
    try:
        routers = await otbr_agent.get_router_table()
        return {"routers": routers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network/info")
async def get_network_info():
    """Get comprehensive network information"""
    try:
        info = await otbr_agent.get_network_info()
        return info if info else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network/scan")
async def scan_networks():
    """Scan for available Thread networks"""
    try:
        networks = await otbr_agent.scan_networks()
        return {"networks": networks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network/ping")
async def ping_device(address: str, count: int = 3):
    """Ping a device on the Thread network"""
    try:
        result = await otbr_agent.ping(address, count)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
