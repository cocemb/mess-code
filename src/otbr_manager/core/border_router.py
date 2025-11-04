"""Border Router management"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import BorderRouter, EndDevice
from ..database import get_db_context


logger = logging.getLogger(__name__)


class BorderRouterManager:
    """Manages OpenThread Border Routers"""

    def __init__(self):
        self.active_connections: Dict[int, 'RouterConnection'] = {}

    async def register_router(
        self,
        name: str,
        mac_address: str,
        ip_address: str,
        rcp_version: str,
        **kwargs
    ) -> BorderRouter:
        """Register a new border router"""
        with get_db_context() as db:
            router = BorderRouter(
                name=name,
                mac_address=mac_address,
                ip_address=ip_address,
                rcp_version=rcp_version,
                status="online",
                **kwargs
            )
            db.add(router)
            db.commit()
            db.refresh(router)

            logger.info(f"Registered new border router: {name} ({mac_address})")
            return router

    async def update_router_status(
        self,
        router_id: int,
        status: str,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """Update router status and metrics"""
        with get_db_context() as db:
            router = db.query(BorderRouter).filter(BorderRouter.id == router_id).first()
            if not router:
                raise ValueError(f"Router {router_id} not found")

            router.status = status
            router.last_seen = datetime.utcnow()

            if metrics:
                if 'device_count' in metrics:
                    router.device_count = metrics['device_count']
                if 'uptime_seconds' in metrics:
                    router.uptime_seconds = metrics['uptime_seconds']

            db.commit()

    async def get_router(self, router_id: int) -> Optional[BorderRouter]:
        """Get router by ID"""
        with get_db_context() as db:
            return db.query(BorderRouter).filter(BorderRouter.id == router_id).first()

    async def list_routers(
        self,
        status: Optional[str] = None,
        topology_id: Optional[int] = None
    ) -> List[BorderRouter]:
        """List all routers with optional filters"""
        with get_db_context() as db:
            query = db.query(BorderRouter)

            if status:
                query = query.filter(BorderRouter.status == status)
            if topology_id:
                query = query.filter(BorderRouter.topology_id == topology_id)

            return query.all()

    async def configure_network(
        self,
        router_id: int,
        network_name: str,
        pan_id: str,
        channel: int,
        extended_pan_id: Optional[str] = None,
        network_key: Optional[str] = None
    ):
        """Configure OpenThread network parameters"""
        with get_db_context() as db:
            router = db.query(BorderRouter).filter(BorderRouter.id == router_id).first()
            if not router:
                raise ValueError(f"Router {router_id} not found")

            router.network_name = network_name
            router.pan_id = pan_id
            router.channel = channel
            if extended_pan_id:
                router.extended_pan_id = extended_pan_id
            if network_key:
                router.network_key = network_key

            db.commit()

            logger.info(f"Configured network for router {router.name}: {network_name}")

    async def get_router_metrics(self, router_id: int) -> Dict[str, Any]:
        """Get comprehensive router metrics"""
        with get_db_context() as db:
            router = db.query(BorderRouter).filter(BorderRouter.id == router_id).first()
            if not router:
                raise ValueError(f"Router {router_id} not found")

            device_count = db.query(EndDevice).filter(
                EndDevice.border_router_id == router_id
            ).count()

            online_devices = db.query(EndDevice).filter(
                EndDevice.border_router_id == router_id,
                EndDevice.status == "online"
            ).count()

            return {
                "router_id": router.id,
                "name": router.name,
                "status": router.status,
                "uptime_seconds": router.uptime_seconds,
                "total_devices": device_count,
                "online_devices": online_devices,
                "offline_devices": device_count - online_devices,
                "network_name": router.network_name,
                "channel": router.channel,
                "last_seen": router.last_seen.isoformat() if router.last_seen else None
            }

    async def delete_router(self, router_id: int):
        """Delete a border router"""
        with get_db_context() as db:
            router = db.query(BorderRouter).filter(BorderRouter.id == router_id).first()
            if not router:
                raise ValueError(f"Router {router_id} not found")

            # Remove from active connections
            if router_id in self.active_connections:
                del self.active_connections[router_id]

            db.delete(router)
            db.commit()

            logger.info(f"Deleted border router: {router.name}")


# Singleton instance
border_router_manager = BorderRouterManager()
