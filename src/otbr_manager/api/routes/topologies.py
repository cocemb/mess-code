"""Topology API routes"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.topology import topology_manager


router = APIRouter()


class TopologyCreate(BaseModel):
    name: str
    topology_type: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class StarTopologyCreate(BaseModel):
    name: str
    primary_router_id: int
    backup_router_ids: Optional[List[int]] = None


class MeshTopologyCreate(BaseModel):
    name: str
    router_ids: List[int]


class TreeTopologyCreate(BaseModel):
    name: str
    root_router_id: int
    child_router_ids: List[int]


class RouterAssignment(BaseModel):
    router_id: int
    role: str = "mesh_node"


@router.post("/")
async def create_topology(topology: TopologyCreate):
    """Create a new topology"""
    try:
        created = await topology_manager.create_topology(
            name=topology.name,
            topology_type=topology.topology_type,
            description=topology.description,
            config=topology.config
        )
        return {
            "id": created.id,
            "name": created.name,
            "type": created.topology_type
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/star")
async def create_star_topology(topology: StarTopologyCreate):
    """Create a star topology"""
    try:
        created = await topology_manager.create_star_topology(
            name=topology.name,
            primary_router_id=topology.primary_router_id,
            backup_router_ids=topology.backup_router_ids
        )
        return {
            "id": created.id,
            "name": created.name,
            "type": "star"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mesh")
async def create_mesh_topology(topology: MeshTopologyCreate):
    """Create a mesh topology"""
    try:
        created = await topology_manager.create_mesh_topology(
            name=topology.name,
            router_ids=topology.router_ids
        )
        return {
            "id": created.id,
            "name": created.name,
            "type": "mesh"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tree")
async def create_tree_topology(topology: TreeTopologyCreate):
    """Create a tree topology"""
    try:
        created = await topology_manager.create_tree_topology(
            name=topology.name,
            root_router_id=topology.root_router_id,
            child_router_ids=topology.child_router_ids
        )
        return {
            "id": created.id,
            "name": created.name,
            "type": "tree"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_topologies(active_only: bool = True):
    """List all topologies"""
    topologies = await topology_manager.list_topologies(active_only)
    return [
        {
            "id": t.id,
            "name": t.name,
            "type": t.topology_type,
            "is_active": t.is_active,
            "description": t.description
        }
        for t in topologies
    ]


@router.get("/{topology_id}")
async def get_topology(topology_id: int):
    """Get topology details"""
    topology = await topology_manager.get_topology(topology_id)
    if not topology:
        raise HTTPException(status_code=404, detail="Topology not found")

    return {
        "id": topology.id,
        "name": topology.name,
        "type": topology.topology_type,
        "description": topology.description,
        "config": topology.config,
        "is_active": topology.is_active
    }


@router.get("/{topology_id}/routers")
async def get_topology_routers(topology_id: int):
    """Get all routers in a topology"""
    routers = await topology_manager.get_topology_routers(topology_id)
    return [
        {
            "id": r.id,
            "name": r.name,
            "role": r.topology_role,
            "status": r.status
        }
        for r in routers
    ]


@router.get("/{topology_id}/visualization")
async def get_topology_visualization(topology_id: int):
    """Get topology visualization data"""
    try:
        viz = await topology_manager.get_topology_visualization(topology_id)
        return viz
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{topology_id}/assign-router")
async def assign_router(topology_id: int, assignment: RouterAssignment):
    """Assign a router to topology"""
    try:
        await topology_manager.assign_router_to_topology(
            router_id=assignment.router_id,
            topology_id=topology_id,
            role=assignment.role
        )
        return {"status": "assigned"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{topology_id}/remove-router/{router_id}")
async def remove_router(topology_id: int, router_id: int):
    """Remove a router from topology"""
    try:
        await topology_manager.remove_router_from_topology(router_id)
        return {"status": "removed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{topology_id}/config")
async def update_topology_config(topology_id: int, config: Dict[str, Any]):
    """Update topology configuration"""
    try:
        await topology_manager.update_topology_config(topology_id, config)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{topology_id}")
async def delete_topology(topology_id: int):
    """Delete a topology"""
    try:
        await topology_manager.delete_topology(topology_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
