#!/usr/bin/env python3
"""
Basic usage examples for OT-BRM

This script demonstrates common operations:
1. Register a border router
2. Register devices
3. Create a topology
4. Schedule firmware updates
5. Query device statistics
"""

import asyncio
import aiohttp
from datetime import datetime


API_BASE = "http://localhost:8000/api/v1"


async def register_border_router(session):
    """Register a border router"""
    print("1. Registering border router...")

    data = {
        "name": "BR-Main",
        "mac_address": "00:11:22:33:44:55",
        "ip_address": "192.168.1.100",
        "rcp_version": "1.0.0",
        "network_name": "TestNetwork",
        "pan_id": "1234",
        "channel": 15
    }

    async with session.post(f"{API_BASE}/routers", json=data) as resp:
        result = await resp.json()
        print(f"   Router registered: {result}")
        return result["id"]


async def register_devices(session, router_id, count=10):
    """Register multiple devices"""
    print(f"\n2. Registering {count} devices...")

    devices = [
        {
            "eui64": f"00112233445566{i:02x}",
            "border_router_id": router_id,
            "device_type": "sed",
            "name": f"Device-{i:02d}"
        }
        for i in range(count)
    ]

    async with session.post(f"{API_BASE}/devices/bulk", json=devices) as resp:
        result = await resp.json()
        print(f"   Devices registered: {result['count']}")
        return result


async def create_mesh_topology(session, router_ids):
    """Create a mesh topology"""
    print("\n3. Creating mesh topology...")

    data = {
        "name": "Test-Mesh",
        "router_ids": router_ids
    }

    async with session.post(f"{API_BASE}/topologies/mesh", json=data) as resp:
        result = await resp.json()
        print(f"   Topology created: {result}")
        return result["id"]


async def get_device_statistics(session):
    """Get device statistics"""
    print("\n4. Getting device statistics...")

    async with session.get(f"{API_BASE}/devices/statistics") as resp:
        stats = await resp.json()
        print(f"   Total devices: {stats['total_devices']}")
        print(f"   Online: {stats['online']}")
        print(f"   Offline: {stats['offline']}")
        print(f"   Average RSSI: {stats['average_rssi']} dBm")
        return stats


async def register_firmware(session):
    """Register a firmware version"""
    print("\n5. Registering firmware version...")

    data = {
        "version": "2.0.0",
        "file_path": "/app/firmware/firmware-2.0.0.bin",
        "device_types": ["sed", "med"],
        "description": "New firmware with bug fixes",
        "release_notes": "- Fixed connectivity issues\n- Improved battery life"
    }

    async with session.post(f"{API_BASE}/firmware/versions", json=data) as resp:
        result = await resp.json()
        print(f"   Firmware registered: {result}")
        return result["id"]


async def schedule_firmware_update(session, device_id, firmware_id):
    """Schedule a firmware update"""
    print("\n6. Scheduling firmware update...")

    data = {
        "device_id": device_id,
        "firmware_version_id": firmware_id
    }

    async with session.post(f"{API_BASE}/firmware/updates/schedule", json=data) as resp:
        result = await resp.json()
        print(f"   Update scheduled: {result}")
        return result["update_id"]


async def register_sensor(session, device_id):
    """Register a sensor"""
    print("\n7. Registering sensor...")

    data = {
        "device_id": device_id,
        "sensor_type": "temperature",
        "name": "Temp-01",
        "unit": "°C",
        "sampling_interval": 60,
        "threshold_min": 10.0,
        "threshold_max": 30.0
    }

    async with session.post(f"{API_BASE}/sensors", json=data) as resp:
        result = await resp.json()
        print(f"   Sensor registered: {result}")
        return result["id"]


async def record_sensor_reading(session, sensor_id, value):
    """Record a sensor reading"""
    print(f"\n8. Recording sensor reading: {value}°C...")

    data = {
        "sensor_id": sensor_id,
        "value": value,
        "timestamp": datetime.utcnow().isoformat()
    }

    async with session.post(f"{API_BASE}/sensors/readings", json=data) as resp:
        result = await resp.json()
        print(f"   Reading recorded: {result}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("OpenThread Border Router Manager - Basic Usage Examples")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Register border router
            router_id = await register_border_router(session)

            # 2. Register devices
            await register_devices(session, router_id, count=10)

            # 3. Create topology (need multiple routers for mesh)
            # In real scenario, register multiple routers first

            # 4. Get statistics
            await get_device_statistics(session)

            # 5. Register firmware
            firmware_id = await register_firmware(session)

            # 6. Schedule update for first device
            # await schedule_firmware_update(session, device_id=1, firmware_id=firmware_id)

            # 7. Register sensor on first device
            sensor_id = await register_sensor(session, device_id=1)

            # 8. Record some sensor readings
            await record_sensor_reading(session, sensor_id, 22.5)
            await record_sensor_reading(session, sensor_id, 23.1)

            print("\n" + "=" * 60)
            print("All examples completed successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
