"""End Device management - optimized for 1000+ devices"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models import EndDevice, BorderRouter, DeviceStatus
from ..database import get_db_context


logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages OpenThread end devices with scale optimization"""

    def __init__(self):
        self.device_cache: Dict[str, EndDevice] = {}
        self.cache_ttl = 60  # seconds

    async def register_device(
        self,
        eui64: str,
        border_router_id: int,
        device_type: str = "sed",
        name: Optional[str] = None,
        **kwargs
    ) -> EndDevice:
        """Register a new end device"""
        with get_db_context() as db:
            # Check if device already exists
            existing = db.query(EndDevice).filter(EndDevice.eui64 == eui64).first()
            if existing:
                logger.warning(f"Device {eui64} already exists, updating...")
                existing.border_router_id = border_router_id
                existing.status = "online"
                existing.last_seen = datetime.utcnow()
                db.commit()
                db.refresh(existing)
                return existing

            device = EndDevice(
                eui64=eui64,
                border_router_id=border_router_id,
                device_type=device_type,
                name=name or f"Device-{eui64[-8:]}",
                status="online",
                **kwargs
            )
            db.add(device)
            db.commit()
            db.refresh(device)

            logger.info(f"Registered new device: {device.name} ({eui64})")
            return device

    async def bulk_register_devices(
        self,
        devices: List[Dict[str, Any]]
    ) -> List[EndDevice]:
        """Bulk register devices for efficiency at scale"""
        with get_db_context() as db:
            registered = []

            # Process in batches of 100 for optimal performance
            batch_size = 100
            for i in range(0, len(devices), batch_size):
                batch = devices[i:i + batch_size]

                for device_data in batch:
                    eui64 = device_data['eui64']
                    existing = db.query(EndDevice).filter(
                        EndDevice.eui64 == eui64
                    ).first()

                    if existing:
                        # Update existing device
                        for key, value in device_data.items():
                            setattr(existing, key, value)
                        existing.last_seen = datetime.utcnow()
                        registered.append(existing)
                    else:
                        # Create new device
                        device = EndDevice(**device_data)
                        db.add(device)
                        registered.append(device)

                # Commit batch
                db.commit()
                logger.info(f"Bulk registered batch {i//batch_size + 1}: {len(batch)} devices")

            return registered

    async def update_device_status(
        self,
        device_id: int,
        status: str,
        rssi: Optional[int] = None,
        link_quality: Optional[int] = None
    ):
        """Update device status and metrics"""
        with get_db_context() as db:
            device = db.query(EndDevice).filter(EndDevice.id == device_id).first()
            if not device:
                raise ValueError(f"Device {device_id} not found")

            device.status = status
            device.last_seen = datetime.utcnow()

            if rssi is not None:
                device.rssi = rssi
            if link_quality is not None:
                device.link_quality = link_quality

            db.commit()

    async def get_device(
        self,
        device_id: Optional[int] = None,
        eui64: Optional[str] = None
    ) -> Optional[EndDevice]:
        """Get device by ID or EUI64"""
        with get_db_context() as db:
            if device_id:
                return db.query(EndDevice).filter(EndDevice.id == device_id).first()
            elif eui64:
                return db.query(EndDevice).filter(EndDevice.eui64 == eui64).first()
            return None

    async def list_devices(
        self,
        border_router_id: Optional[int] = None,
        status: Optional[str] = None,
        device_type: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List devices with pagination for handling 1000+ devices
        Returns devices with total count for pagination
        """
        with get_db_context() as db:
            query = db.query(EndDevice)

            # Apply filters
            if border_router_id:
                query = query.filter(EndDevice.border_router_id == border_router_id)
            if status:
                query = query.filter(EndDevice.status == status)
            if device_type:
                query = query.filter(EndDevice.device_type == device_type)

            # Get total count before pagination
            total_count = query.count()

            # Apply pagination
            devices = query.offset(offset).limit(limit).all()

            return {
                "devices": devices,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }

    async def search_devices(
        self,
        search_term: str,
        limit: int = 100
    ) -> List[EndDevice]:
        """Search devices by name or EUI64"""
        with get_db_context() as db:
            return db.query(EndDevice).filter(
                (EndDevice.name.like(f"%{search_term}%")) |
                (EndDevice.eui64.like(f"%{search_term}%"))
            ).limit(limit).all()

    async def get_device_statistics(
        self,
        border_router_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get device statistics - optimized for large datasets"""
        with get_db_context() as db:
            query = db.query(EndDevice)

            if border_router_id:
                query = query.filter(EndDevice.border_router_id == border_router_id)

            # Aggregate statistics
            total = query.count()
            online = query.filter(EndDevice.status == "online").count()
            offline = query.filter(EndDevice.status == "offline").count()
            sleeping = query.filter(EndDevice.status == "sleeping").count()

            # Device type breakdown
            device_types = db.query(
                EndDevice.device_type,
                func.count(EndDevice.id)
            ).group_by(EndDevice.device_type).all()

            # Average RSSI
            avg_rssi = db.query(func.avg(EndDevice.rssi)).filter(
                EndDevice.rssi.isnot(None),
                EndDevice.status == "online"
            ).scalar() or 0

            return {
                "total_devices": total,
                "online": online,
                "offline": offline,
                "sleeping": sleeping,
                "device_types": dict(device_types),
                "average_rssi": round(avg_rssi, 2)
            }

    async def detect_stale_devices(
        self,
        threshold_minutes: int = 60
    ) -> List[EndDevice]:
        """
        Detect devices that haven't been seen for a while
        Useful for maintaining accurate state with 1000+ devices
        """
        with get_db_context() as db:
            threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)

            stale_devices = db.query(EndDevice).filter(
                EndDevice.status == "online",
                EndDevice.last_seen < threshold_time
            ).all()

            # Mark as offline
            for device in stale_devices:
                device.status = "offline"

            db.commit()

            logger.info(f"Marked {len(stale_devices)} stale devices as offline")
            return stale_devices

    async def update_device_metadata(
        self,
        device_id: int,
        metadata: Dict[str, Any]
    ):
        """Update device metadata"""
        with get_db_context() as db:
            device = db.query(EndDevice).filter(EndDevice.id == device_id).first()
            if not device:
                raise ValueError(f"Device {device_id} not found")

            device.metadata = metadata
            db.commit()

    async def delete_device(self, device_id: int):
        """Delete a device"""
        with get_db_context() as db:
            device = db.query(EndDevice).filter(EndDevice.id == device_id).first()
            if not device:
                raise ValueError(f"Device {device_id} not found")

            db.delete(device)
            db.commit()

            logger.info(f"Deleted device: {device.name}")

    async def get_device_tree(
        self,
        border_router_id: int
    ) -> Dict[str, Any]:
        """
        Get hierarchical device tree for network visualization
        Shows parent-child relationships
        """
        with get_db_context() as db:
            devices = db.query(EndDevice).filter(
                EndDevice.border_router_id == border_router_id
            ).all()

            # Build tree structure
            device_map = {d.id: d for d in devices}
            tree = []

            for device in devices:
                if device.parent_id is None:
                    # Root level device
                    tree.append(self._build_device_node(device, device_map))

            return {
                "border_router_id": border_router_id,
                "device_count": len(devices),
                "tree": tree
            }

    def _build_device_node(
        self,
        device: EndDevice,
        device_map: Dict[int, EndDevice]
    ) -> Dict[str, Any]:
        """Build device tree node recursively"""
        node = {
            "id": device.id,
            "eui64": device.eui64,
            "name": device.name,
            "type": device.device_type,
            "status": device.status,
            "rssi": device.rssi,
            "children": []
        }

        # Find children
        for dev_id, dev in device_map.items():
            if dev.parent_id == device.id:
                node["children"].append(self._build_device_node(dev, device_map))

        return node


# Singleton instance
device_manager = DeviceManager()
