"""Cloud connectivity API routes"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...cloud.cloud_manager import cloud_manager, CloudConnectionType


router = APIRouter()


class CloudConnectionConfig(BaseModel):
    name: str
    connection_type: CloudConnectionType
    config: Dict[str, Any]


class TelemetryPublish(BaseModel):
    device_id: str
    data: Dict[str, Any]
    connection: Optional[str] = None


class EventPublish(BaseModel):
    event_type: str
    data: Dict[str, Any]
    connections: Optional[List[str]] = None


class ShadowUpdate(BaseModel):
    device_id: str
    reported_state: Dict[str, Any]
    connection: Optional[str] = None


@router.post("/connections")
async def add_cloud_connection(connection: CloudConnectionConfig):
    """
    Add a cloud connection

    Example configs:

    Generic MQTT:
    ```json
    {
      "name": "mqtt-broker",
      "connection_type": "mqtt",
      "config": {
        "broker": "mqtt.example.com",
        "port": 8883,
        "use_tls": true,
        "ca_cert": "/path/to/ca.crt",
        "client_cert": "/path/to/client.crt",
        "client_key": "/path/to/client.key"
      }
    }
    ```

    AWS IoT Core:
    ```json
    {
      "name": "aws-iot",
      "connection_type": "aws_iot",
      "config": {
        "endpoint": "xxxxx.iot.us-east-1.amazonaws.com",
        "cert_path": "/path/to/certificate.pem.crt",
        "key_path": "/path/to/private.pem.key",
        "ca_path": "/path/to/AmazonRootCA1.pem",
        "region": "us-east-1"
      }
    }
    ```

    Azure IoT Hub:
    ```json
    {
      "name": "azure-iot",
      "connection_type": "azure_iot",
      "config": {
        "connection_string": "HostName=xxx.azure-devices.net;DeviceId=xxx;SharedAccessKey=xxx",
        "device_id": "otbr-manager"
      }
    }
    ```
    """
    try:
        await cloud_manager.add_connection(
            name=connection.name,
            connection_type=connection.connection_type,
            config=connection.config
        )
        return {"status": "connected", "name": connection.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connections/{name}")
async def remove_cloud_connection(name: str):
    """Remove a cloud connection"""
    try:
        await cloud_manager.remove_connection(name)
        return {"status": "disconnected", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections")
async def list_cloud_connections():
    """List active cloud connections"""
    return {
        "connections": list(cloud_manager.connections.keys()),
        "count": len(cloud_manager.connections)
    }


@router.post("/start")
async def start_cloud_manager():
    """Start cloud manager background tasks"""
    try:
        await cloud_manager.start()
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_cloud_manager():
    """Stop cloud manager background tasks"""
    try:
        await cloud_manager.stop()
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_cloud_status():
    """Get cloud manager status"""
    return {
        "running": cloud_manager.is_running,
        "connections": len(cloud_manager.connections),
        "telemetry_interval": cloud_manager.telemetry_interval,
        "sync_interval": cloud_manager.sync_interval
    }


@router.post("/telemetry/publish")
async def publish_telemetry(data: TelemetryPublish):
    """Manually publish telemetry for a device"""
    try:
        await cloud_manager.publish_device_telemetry(
            device_id=data.device_id,
            data=data.data,
            connection=data.connection
        )
        return {"status": "published"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/publish")
async def publish_event(event: EventPublish):
    """Publish an event to cloud"""
    try:
        await cloud_manager.publish_event(
            event_type=event.event_type,
            data=event.data,
            connections=event.connections
        )
        return {"status": "published"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shadow/update")
async def update_shadow(shadow: ShadowUpdate):
    """Update device shadow/digital twin"""
    try:
        await cloud_manager.update_device_shadow(
            device_id=shadow.device_id,
            reported_state=shadow.reported_state,
            connection=shadow.connection
        )
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/intervals")
async def update_intervals(telemetry_interval: int = 60, sync_interval: int = 300):
    """Update telemetry and sync intervals (in seconds)"""
    cloud_manager.telemetry_interval = telemetry_interval
    cloud_manager.sync_interval = sync_interval

    return {
        "telemetry_interval": telemetry_interval,
        "sync_interval": sync_interval
    }
