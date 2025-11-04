"""Multi-router topology management"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import Topology, BorderRouter
from ..database import get_db_context


logger = logging.getLogger(__name__)


class TopologyManager:
    """Manages multi-router topologies and configurations"""

    async def create_topology(
        self,
        name: str,
        topology_type: str,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Topology:
        """Create a new topology configuration"""
        with get_db_context() as db:
            topology = Topology(
                name=name,
                topology_type=topology_type,
                description=description,
                config=config or {},
                is_active=True
            )
            db.add(topology)
            db.commit()
            db.refresh(topology)

            logger.info(f"Created topology: {name} ({topology_type})")
            return topology

    async def get_topology(self, topology_id: int) -> Optional[Topology]:
        """Get topology by ID"""
        with get_db_context() as db:
            return db.query(Topology).filter(Topology.id == topology_id).first()

    async def list_topologies(self, active_only: bool = True) -> List[Topology]:
        """List all topologies"""
        with get_db_context() as db:
            query = db.query(Topology)
            if active_only:
                query = query.filter(Topology.is_active == True)
            return query.all()

    async def update_topology_config(
        self,
        topology_id: int,
        config: Dict[str, Any]
    ):
        """Update topology configuration"""
        with get_db_context() as db:
            topology = db.query(Topology).filter(Topology.id == topology_id).first()
            if not topology:
                raise ValueError(f"Topology {topology_id} not found")

            topology.config = config
            topology.updated_at = datetime.utcnow()
            db.commit()

            logger.info(f"Updated topology config: {topology.name}")

    async def assign_router_to_topology(
        self,
        router_id: int,
        topology_id: int,
        role: str = "mesh_node"
    ):
        """Assign a border router to a topology with a specific role"""
        with get_db_context() as db:
            router = db.query(BorderRouter).filter(BorderRouter.id == router_id).first()
            if not router:
                raise ValueError(f"Router {router_id} not found")

            topology = db.query(Topology).filter(Topology.id == topology_id).first()
            if not topology:
                raise ValueError(f"Topology {topology_id} not found")

            router.topology_id = topology_id
            router.topology_role = role
            db.commit()

            logger.info(f"Assigned router {router.name} to topology {topology.name} as {role}")

    async def remove_router_from_topology(self, router_id: int):
        """Remove a border router from its topology"""
        with get_db_context() as db:
            router = db.query(BorderRouter).filter(BorderRouter.id == router_id).first()
            if not router:
                raise ValueError(f"Router {router_id} not found")

            router.topology_id = None
            router.topology_role = None
            db.commit()

            logger.info(f"Removed router {router.name} from topology")

    async def get_topology_routers(self, topology_id: int) -> List[BorderRouter]:
        """Get all routers in a topology"""
        with get_db_context() as db:
            return db.query(BorderRouter).filter(
                BorderRouter.topology_id == topology_id
            ).all()

    async def create_star_topology(
        self,
        name: str,
        primary_router_id: int,
        backup_router_ids: Optional[List[int]] = None
    ) -> Topology:
        """Create a star topology with one primary and optional backup routers"""
        config = {
            "type": "star",
            "primary_router_id": primary_router_id,
            "backup_router_ids": backup_router_ids or [],
            "failover_enabled": bool(backup_router_ids)
        }

        topology = await self.create_topology(
            name=name,
            topology_type="star",
            config=config
        )

        # Assign routers
        await self.assign_router_to_topology(primary_router_id, topology.id, "primary")

        if backup_router_ids:
            for backup_id in backup_router_ids:
                await self.assign_router_to_topology(backup_id, topology.id, "backup")

        return topology

    async def create_mesh_topology(
        self,
        name: str,
        router_ids: List[int]
    ) -> Topology:
        """Create a mesh topology with multiple interconnected routers"""
        config = {
            "type": "mesh",
            "router_ids": router_ids,
            "mesh_degree": len(router_ids)
        }

        topology = await self.create_topology(
            name=name,
            topology_type="mesh",
            config=config
        )

        # Assign all routers as mesh nodes
        for router_id in router_ids:
            await self.assign_router_to_topology(router_id, topology.id, "mesh_node")

        return topology

    async def create_tree_topology(
        self,
        name: str,
        root_router_id: int,
        child_router_ids: List[int]
    ) -> Topology:
        """Create a tree topology with a root and child routers"""
        config = {
            "type": "tree",
            "root_router_id": root_router_id,
            "child_router_ids": child_router_ids,
            "depth": 2  # Can be extended for deeper trees
        }

        topology = await self.create_topology(
            name=name,
            topology_type="tree",
            config=config
        )

        # Assign routers
        await self.assign_router_to_topology(root_router_id, topology.id, "root")

        for child_id in child_router_ids:
            await self.assign_router_to_topology(child_id, topology.id, "child")

        return topology

    async def get_topology_visualization(
        self,
        topology_id: int
    ) -> Dict[str, Any]:
        """Get topology data for visualization"""
        with get_db_context() as db:
            topology = db.query(Topology).filter(Topology.id == topology_id).first()
            if not topology:
                raise ValueError(f"Topology {topology_id} not found")

            routers = db.query(BorderRouter).filter(
                BorderRouter.topology_id == topology_id
            ).all()

            # Build visualization data
            nodes = []
            edges = []

            for router in routers:
                nodes.append({
                    "id": router.id,
                    "name": router.name,
                    "role": router.topology_role,
                    "status": router.status,
                    "device_count": router.device_count
                })

            # Build edges based on topology type
            if topology.topology_type == "star":
                primary_id = topology.config.get("primary_router_id")
                for router in routers:
                    if router.id != primary_id:
                        edges.append({
                            "source": primary_id,
                            "target": router.id,
                            "type": "backup" if router.topology_role == "backup" else "connection"
                        })

            elif topology.topology_type == "mesh":
                # Full mesh - connect all nodes
                for i, router1 in enumerate(routers):
                    for router2 in routers[i+1:]:
                        edges.append({
                            "source": router1.id,
                            "target": router2.id,
                            "type": "mesh"
                        })

            elif topology.topology_type == "tree":
                root_id = topology.config.get("root_router_id")
                for router in routers:
                    if router.id != root_id:
                        edges.append({
                            "source": root_id,
                            "target": router.id,
                            "type": "tree"
                        })

            return {
                "topology_id": topology_id,
                "name": topology.name,
                "type": topology.topology_type,
                "nodes": nodes,
                "edges": edges,
                "config": topology.config
            }

    async def delete_topology(self, topology_id: int):
        """Delete a topology"""
        with get_db_context() as db:
            topology = db.query(Topology).filter(Topology.id == topology_id).first()
            if not topology:
                raise ValueError(f"Topology {topology_id} not found")

            # Remove routers from topology first
            routers = db.query(BorderRouter).filter(
                BorderRouter.topology_id == topology_id
            ).all()

            for router in routers:
                router.topology_id = None
                router.topology_role = None

            db.delete(topology)
            db.commit()

            logger.info(f"Deleted topology: {topology.name}")


# Singleton instance
topology_manager = TopologyManager()
