"""Border Router API routes"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.border_router import border_router_manager


router = APIRouter()


class RouterCreate(BaseModel):
    name: str
    mac_address: str
    ip_address: str
    rcp_version: str
    network_name: Optional[str] = None
    pan_id: Optional[str] = None
    channel: Optional[int] = None


class RouterUpdate(BaseModel):
    status: str
    device_count: Optional[int] = None
    uptime_seconds: Optional[int] = None


class NetworkConfig(BaseModel):
    network_name: str
    pan_id: str
    channel: int
    extended_pan_id: Optional[str] = None
    network_key: Optional[str] = None


@router.post("/")
async def register_router(router_data: RouterCreate):
    """Register a new border router"""
    try:
        router = await border_router_manager.register_router(
            name=router_data.name,
            mac_address=router_data.mac_address,
            ip_address=router_data.ip_address,
            rcp_version=router_data.rcp_version,
            network_name=router_data.network_name,
            pan_id=router_data.pan_id,
            channel=router_data.channel
        )
        return {"id": router.id, "name": router.name, "status": router.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_routers(
    status: Optional[str] = None,
    topology_id: Optional[int] = None
):
    """List all border routers"""
    routers = await border_router_manager.list_routers(
        status=status,
        topology_id=topology_id
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "mac_address": r.mac_address,
            "ip_address": r.ip_address,
            "status": r.status,
            "device_count": r.device_count,
            "network_name": r.network_name,
            "channel": r.channel
        }
        for r in routers
    ]


@router.get("/{router_id}")
async def get_router(router_id: int):
    """Get router details"""
    router = await border_router_manager.get_router(router_id)
    if not router:
        raise HTTPException(status_code=404, detail="Router not found")

    return {
        "id": router.id,
        "name": router.name,
        "mac_address": router.mac_address,
        "ip_address": router.ip_address,
        "rcp_version": router.rcp_version,
        "status": router.status,
        "network_name": router.network_name,
        "pan_id": router.pan_id,
        "channel": router.channel,
        "device_count": router.device_count,
        "uptime_seconds": router.uptime_seconds,
        "last_seen": router.last_seen.isoformat() if router.last_seen else None
    }


@router.put("/{router_id}/status")
async def update_router_status(router_id: int, update: RouterUpdate):
    """Update router status"""
    try:
        await border_router_manager.update_router_status(
            router_id=router_id,
            status=update.status,
            metrics={
                "device_count": update.device_count,
                "uptime_seconds": update.uptime_seconds
            }
        )
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{router_id}/network")
async def configure_network(router_id: int, config: NetworkConfig):
    """Configure OpenThread network"""
    try:
        await border_router_manager.configure_network(
            router_id=router_id,
            network_name=config.network_name,
            pan_id=config.pan_id,
            channel=config.channel,
            extended_pan_id=config.extended_pan_id,
            network_key=config.network_key
        )
        return {"status": "configured"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{router_id}/metrics")
async def get_router_metrics(router_id: int):
    """Get router metrics"""
    try:
        metrics = await border_router_manager.get_router_metrics(router_id)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{router_id}")
async def delete_router(router_id: int):
    """Delete a border router"""
    try:
        await border_router_manager.delete_router(router_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
