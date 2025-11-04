"""Sensor API routes"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...core.sensor import sensor_manager


router = APIRouter()


class SensorCreate(BaseModel):
    device_id: int
    sensor_type: str
    name: str
    unit: str
    sampling_interval: int = 60
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None


class ReadingCreate(BaseModel):
    sensor_id: int
    value: float
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class SensorConfigUpdate(BaseModel):
    sampling_interval: Optional[int] = None
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None


@router.post("/")
async def register_sensor(sensor: SensorCreate):
    """Register a new sensor"""
    try:
        registered = await sensor_manager.register_sensor(
            device_id=sensor.device_id,
            sensor_type=sensor.sensor_type,
            name=sensor.name,
            unit=sensor.unit,
            sampling_interval=sensor.sampling_interval,
            threshold_min=sensor.threshold_min,
            threshold_max=sensor.threshold_max
        )
        return {
            "id": registered.id,
            "name": registered.name,
            "sensor_type": registered.sensor_type
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_sensors(
    device_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    active_only: bool = True
):
    """List sensors"""
    sensors = await sensor_manager.list_sensors(
        device_id=device_id,
        sensor_type=sensor_type,
        active_only=active_only
    )
    return [
        {
            "id": s.id,
            "name": s.name,
            "sensor_type": s.sensor_type,
            "unit": s.unit,
            "device_id": s.device_id,
            "is_active": s.is_active,
            "last_reading_at": s.last_reading_at.isoformat() if s.last_reading_at else None
        }
        for s in sensors
    ]


@router.get("/{sensor_id}")
async def get_sensor(sensor_id: int):
    """Get sensor details"""
    sensor = await sensor_manager.get_sensor(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    return {
        "id": sensor.id,
        "device_id": sensor.device_id,
        "sensor_type": sensor.sensor_type,
        "name": sensor.name,
        "unit": sensor.unit,
        "sampling_interval": sensor.sampling_interval,
        "threshold_min": sensor.threshold_min,
        "threshold_max": sensor.threshold_max,
        "is_active": sensor.is_active,
        "last_reading_at": sensor.last_reading_at.isoformat() if sensor.last_reading_at else None
    }


@router.post("/readings")
async def record_reading(reading: ReadingCreate):
    """Record a sensor reading"""
    try:
        recorded = await sensor_manager.record_reading(
            sensor_id=reading.sensor_id,
            value=reading.value,
            timestamp=reading.timestamp,
            metadata=reading.metadata
        )
        return {
            "id": recorded.id,
            "sensor_id": recorded.sensor_id,
            "value": recorded.value,
            "timestamp": recorded.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/readings/bulk")
async def bulk_record_readings(readings: List[Dict[str, Any]]):
    """Bulk record sensor readings"""
    try:
        count = await sensor_manager.bulk_record_readings(readings)
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{sensor_id}/readings")
async def get_readings(
    sensor_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(default=1000, le=10000)
):
    """Get sensor readings"""
    readings = await sensor_manager.get_readings(
        sensor_id=sensor_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    return [
        {
            "id": r.id,
            "value": r.value,
            "timestamp": r.timestamp.isoformat(),
            "metadata": r.metadata
        }
        for r in readings
    ]


@router.get("/{sensor_id}/readings/latest")
async def get_latest_reading(sensor_id: int):
    """Get latest sensor reading"""
    reading = await sensor_manager.get_latest_reading(sensor_id)
    if not reading:
        return {"message": "No readings found"}

    return {
        "id": reading.id,
        "sensor_id": reading.sensor_id,
        "value": reading.value,
        "timestamp": reading.timestamp.isoformat(),
        "metadata": reading.metadata
    }


@router.get("/{sensor_id}/statistics")
async def get_sensor_statistics(
    sensor_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """Get sensor statistics"""
    try:
        stats = await sensor_manager.get_sensor_statistics(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{sensor_id}/readings/aggregated")
async def get_aggregated_readings(
    sensor_id: int,
    interval_minutes: int = 60,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """Get aggregated sensor readings"""
    try:
        aggregated = await sensor_manager.get_aggregated_readings(
            sensor_id=sensor_id,
            interval_minutes=interval_minutes,
            start_time=start_time,
            end_time=end_time
        )
        return {"data": aggregated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{sensor_id}/config")
async def update_sensor_config(sensor_id: int, config: SensorConfigUpdate):
    """Update sensor configuration"""
    try:
        await sensor_manager.update_sensor_config(
            sensor_id=sensor_id,
            sampling_interval=config.sampling_interval,
            threshold_min=config.threshold_min,
            threshold_max=config.threshold_max
        )
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{sensor_id}")
async def delete_sensor(sensor_id: int):
    """Delete a sensor"""
    try:
        await sensor_manager.delete_sensor(sensor_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/readings/cleanup")
async def cleanup_old_readings(days_to_keep: int = 30):
    """Delete old sensor readings"""
    try:
        deleted = await sensor_manager.delete_old_readings(days_to_keep)
        return {"deleted_count": deleted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
