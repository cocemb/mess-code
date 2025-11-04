"""Attenuator API routes"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.attenuator import attenuator_controller


router = APIRouter()


class AttenuatorCreate(BaseModel):
    name: str
    device_path: str
    model: str = "Generic"
    min_db: float = 0.0
    max_db: float = 90.0


class AttenuationSet(BaseModel):
    attenuation_db: float


class DeviceAssignment(BaseModel):
    device_ids: List[int]


class AttenuationScenario(BaseModel):
    scenario_name: str
    steps: List[Dict[str, Any]]


@router.post("/")
async def register_attenuator(attenuator: AttenuatorCreate):
    """Register a new attenuator"""
    try:
        registered = await attenuator_controller.register_attenuator(
            name=attenuator.name,
            device_path=attenuator.device_path,
            model=attenuator.model,
            min_db=attenuator.min_db,
            max_db=attenuator.max_db
        )
        return {
            "id": registered.id,
            "name": registered.name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_attenuators():
    """List all attenuators"""
    attenuators = await attenuator_controller.list_attenuators()
    return [
        {
            "id": a.id,
            "name": a.name,
            "model": a.model,
            "current_attenuation_db": a.current_attenuation_db,
            "is_enabled": a.is_enabled
        }
        for a in attenuators
    ]


@router.get("/{attenuator_id}")
async def get_attenuator(attenuator_id: int):
    """Get attenuator details"""
    attenuator = await attenuator_controller.get_attenuator(attenuator_id)
    if not attenuator:
        raise HTTPException(status_code=404, detail="Attenuator not found")

    return {
        "id": attenuator.id,
        "name": attenuator.name,
        "device_path": attenuator.device_path,
        "model": attenuator.model,
        "min_attenuation_db": attenuator.min_attenuation_db,
        "max_attenuation_db": attenuator.max_attenuation_db,
        "current_attenuation_db": attenuator.current_attenuation_db,
        "is_enabled": attenuator.is_enabled,
        "affected_devices": attenuator.affected_devices
    }


@router.post("/{attenuator_id}/connect")
async def connect_attenuator(attenuator_id: int):
    """Connect to attenuator device"""
    try:
        await attenuator_controller.connect_attenuator(attenuator_id)
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{attenuator_id}/disconnect")
async def disconnect_attenuator(attenuator_id: int):
    """Disconnect from attenuator device"""
    try:
        await attenuator_controller.disconnect_attenuator(attenuator_id)
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{attenuator_id}/attenuation")
async def set_attenuation(attenuator_id: int, setting: AttenuationSet):
    """Set attenuation level"""
    try:
        await attenuator_controller.set_attenuation(
            attenuator_id=attenuator_id,
            attenuation_db=setting.attenuation_db
        )
        return {
            "status": "set",
            "attenuation_db": setting.attenuation_db
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{attenuator_id}/attenuation")
async def get_attenuation(attenuator_id: int):
    """Get current attenuation level"""
    try:
        attenuation = await attenuator_controller.get_attenuation(attenuator_id)
        return {"attenuation_db": attenuation}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scenario")
async def create_scenario(scenario: AttenuationScenario):
    """Create and execute an attenuation scenario"""
    try:
        await attenuator_controller.create_attenuation_scenario(
            scenario_name=scenario.scenario_name,
            steps=scenario.steps
        )
        return {"status": "completed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{attenuator_id}/assign-devices")
async def assign_devices(attenuator_id: int, assignment: DeviceAssignment):
    """Assign devices to attenuator"""
    try:
        await attenuator_controller.assign_devices_to_attenuator(
            attenuator_id=attenuator_id,
            device_ids=assignment.device_ids
        )
        return {"status": "assigned"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{attenuator_id}/enable")
async def enable_attenuator(attenuator_id: int):
    """Enable an attenuator"""
    try:
        await attenuator_controller.enable_attenuator(attenuator_id)
        return {"status": "enabled"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{attenuator_id}/disable")
async def disable_attenuator(attenuator_id: int):
    """Disable an attenuator"""
    try:
        await attenuator_controller.disable_attenuator(attenuator_id)
        return {"status": "disabled"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ports")
async def list_available_ports():
    """List available serial ports"""
    ports = await attenuator_controller.list_available_ports()
    return {"ports": ports}
