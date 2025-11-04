#!/usr/bin/env python3
"""
Scale test for 1000+ devices

This script demonstrates handling large numbers of devices:
- Bulk register 1000 devices
- Query with pagination
- Update device status
- Performance metrics
"""

import asyncio
import aiohttp
import time
from datetime import datetime


API_BASE = "http://localhost:8000/api/v1"


async def bulk_register_devices(session, router_id, count=1000):
    """Register a large number of devices"""
    print(f"Registering {count} devices...")

    batch_size = 100
    total_time = 0

    for batch_num in range(0, count, batch_size):
        batch_devices = [
            {
                "eui64": f"{i:016x}",
                "border_router_id": router_id,
                "device_type": "sed" if i % 3 == 0 else "med",
                "name": f"Device-{i:04d}"
            }
            for i in range(batch_num, min(batch_num + batch_size, count))
        ]

        start = time.time()
        async with session.post(f"{API_BASE}/devices/bulk", json=batch_devices) as resp:
            result = await resp.json()
            elapsed = time.time() - start
            total_time += elapsed

            print(f"  Batch {batch_num//batch_size + 1}: "
                  f"{result['count']} devices registered in {elapsed:.2f}s")

    print(f"\nTotal: {count} devices registered in {total_time:.2f}s")
    print(f"Average: {count/total_time:.0f} devices/second")


async def paginated_list_devices(session, page_size=100):
    """List devices with pagination"""
    print(f"\nListing devices with pagination (page size: {page_size})...")

    offset = 0
    total = 0
    page = 1

    while True:
        async with session.get(
            f"{API_BASE}/devices",
            params={"limit": page_size, "offset": offset}
        ) as resp:
            result = await resp.json()

            devices_count = len(result["devices"])
            total += devices_count

            print(f"  Page {page}: {devices_count} devices (total: {result['total']})")

            if not result["has_more"]:
                break

            offset += page_size
            page += 1

    print(f"\nTotal devices retrieved: {total}")


async def search_devices(session, query="Device-0"):
    """Search devices"""
    print(f"\nSearching for devices matching '{query}'...")

    start = time.time()
    async with session.get(f"{API_BASE}/devices/search", params={"q": query}) as resp:
        results = await resp.json()
        elapsed = time.time() - start

    print(f"  Found {len(results)} devices in {elapsed:.3f}s")


async def get_device_tree(session, router_id):
    """Get device hierarchy tree"""
    print(f"\nGetting device tree for router {router_id}...")

    start = time.time()
    async with session.get(f"{API_BASE}/devices/router/{router_id}/tree") as resp:
        tree = await resp.json()
        elapsed = time.time() - start

    print(f"  Retrieved tree with {tree['device_count']} devices in {elapsed:.3f}s")


async def bulk_update_status(session, device_count=100):
    """Update status for multiple devices"""
    print(f"\nUpdating status for {device_count} devices...")

    start = time.time()

    tasks = []
    for i in range(1, device_count + 1):
        data = {
            "status": "online",
            "rssi": -50 - (i % 30),
            "link_quality": 80 + (i % 20)
        }
        task = session.put(f"{API_BASE}/devices/{i}/status", json=data)
        tasks.append(task)

    # Execute concurrently
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start
    successful = sum(1 for r in responses if not isinstance(r, Exception))

    print(f"  Updated {successful}/{device_count} devices in {elapsed:.2f}s")
    print(f"  Average: {successful/elapsed:.0f} updates/second")


async def get_statistics(session):
    """Get comprehensive statistics"""
    print("\nGetting device statistics...")

    async with session.get(f"{API_BASE}/devices/statistics") as resp:
        stats = await resp.json()

    print(f"  Total devices: {stats['total_devices']}")
    print(f"  Online: {stats['online']}")
    print(f"  Offline: {stats['offline']}")
    print(f"  Device types: {stats['device_types']}")


async def main():
    """Run scale test"""
    print("=" * 60)
    print("OpenThread Border Router Manager - Scale Test (1000+ devices)")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        try:
            # First, ensure we have a router
            print("\n1. Setting up border router...")
            data = {
                "name": "BR-Scale-Test",
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "ip_address": "192.168.1.200",
                "rcp_version": "1.0.0"
            }
            async with session.post(f"{API_BASE}/routers", json=data) as resp:
                router = await resp.json()
                router_id = router["id"]
                print(f"   Router created: ID {router_id}")

            # 2. Bulk register 1000 devices
            await bulk_register_devices(session, router_id, count=1000)

            # 3. Paginated listing
            await paginated_list_devices(session, page_size=100)

            # 4. Search test
            await search_devices(session, "Device-0")

            # 5. Get device tree
            await get_device_tree(session, router_id)

            # 6. Bulk status updates
            await bulk_update_status(session, device_count=100)

            # 7. Final statistics
            await get_statistics(session)

            print("\n" + "=" * 60)
            print("Scale test completed successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
