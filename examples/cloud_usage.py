#!/usr/bin/env python3
"""
Cloud Connectivity Usage Examples

Demonstrates connecting to various cloud platforms and publishing telemetry.
"""

import asyncio
import aiohttp
import json


API_BASE = "http://localhost:8000/api/v1"


async def setup_aws_iot(session):
    """Setup AWS IoT Core connection"""
    print("1. Setting up AWS IoT Core connection...")

    config = {
        "name": "aws-iot",
        "connection_type": "aws_iot",
        "config": {
            "endpoint": "a3xxxxxxxxxx-ats.iot.us-east-1.amazonaws.com",
            "cert_path": "/path/to/certificate.pem.crt",
            "key_path": "/path/to/private.pem.key",
            "ca_path": "/path/to/AmazonRootCA1.pem",
            "region": "us-east-1"
        }
    }

    async with session.post(f"{API_BASE}/cloud/connections", json=config) as resp:
        result = await resp.json()
        print(f"   AWS IoT connected: {result}")


async def setup_azure_iot(session):
    """Setup Azure IoT Hub connection"""
    print("\n2. Setting up Azure IoT Hub connection...")

    config = {
        "name": "azure-iot",
        "connection_type": "azure_iot",
        "config": {
            "connection_string": "HostName=your-hub.azure-devices.net;DeviceId=otbr-manager;SharedAccessKey=xxxx",
            "device_id": "otbr-manager"
        }
    }

    async with session.post(f"{API_BASE}/cloud/connections", json=config) as resp:
        result = await resp.json()
        print(f"   Azure IoT connected: {result}")


async def setup_mqtt_broker(session):
    """Setup generic MQTT broker connection"""
    print("\n3. Setting up MQTT broker connection...")

    config = {
        "name": "mqtt-broker",
        "connection_type": "mqtt",
        "config": {
            "broker": "mqtt.example.com",
            "port": 8883,
            "provider": "generic_mqtt",
            "use_tls": True,
            "ca_cert": "/path/to/ca.crt",
            "client_cert": "/path/to/client.crt",
            "client_key": "/path/to/client.key"
        }
    }

    async with session.post(f"{API_BASE}/cloud/connections", json=config) as resp:
        result = await resp.json()
        print(f"   MQTT broker connected: {result}")


async def start_cloud_manager(session):
    """Start cloud manager"""
    print("\n4. Starting cloud manager...")

    async with session.post(f"{API_BASE}/cloud/start") as resp:
        result = await resp.json()
        print(f"   Cloud manager started: {result}")


async def publish_manual_telemetry(session):
    """Manually publish telemetry"""
    print("\n5. Publishing manual telemetry...")

    telemetry = {
        "device_id": "0011223344556677",
        "data": {
            "temperature": 23.5,
            "humidity": 45.2,
            "battery": 85,
            "status": "online"
        }
    }

    async with session.post(f"{API_BASE}/cloud/telemetry/publish", json=telemetry) as resp:
        result = await resp.json()
        print(f"   Telemetry published: {result}")


async def publish_event(session):
    """Publish an event"""
    print("\n6. Publishing event...")

    event = {
        "event_type": "device_joined",
        "data": {
            "device_id": "0011223344556677",
            "device_name": "New Temperature Sensor",
            "border_router_id": 1
        }
    }

    async with session.post(f"{API_BASE}/cloud/events/publish", json=event) as resp:
        result = await resp.json()
        print(f"   Event published: {result}")


async def update_device_shadow(session):
    """Update device shadow/digital twin"""
    print("\n7. Updating device shadow...")

    shadow = {
        "device_id": "0011223344556677",
        "reported_state": {
            "status": "online",
            "temperature": 23.5,
            "humidity": 45.2,
            "firmware_version": "1.0.0",
            "last_update": "2025-11-04T12:00:00Z"
        }
    }

    async with session.post(f"{API_BASE}/cloud/shadow/update", json=shadow) as resp:
        result = await resp.json()
        print(f"   Shadow updated: {result}")


async def get_cloud_status(session):
    """Get cloud connection status"""
    print("\n8. Getting cloud status...")

    async with session.get(f"{API_BASE}/cloud/status") as resp:
        status = await resp.json()
        print(f"   Status: {json.dumps(status, indent=2)}")


async def list_connections(session):
    """List active cloud connections"""
    print("\n9. Listing cloud connections...")

    async with session.get(f"{API_BASE}/cloud/connections") as resp:
        connections = await resp.json()
        print(f"   Connections: {json.dumps(connections, indent=2)}")


async def configure_intervals(session):
    """Configure telemetry and sync intervals"""
    print("\n10. Configuring intervals...")

    # Set telemetry every 30 seconds, sync every 5 minutes
    async with session.put(
        f"{API_BASE}/cloud/config/intervals",
        params={"telemetry_interval": 30, "sync_interval": 300}
    ) as resp:
        result = await resp.json()
        print(f"   Intervals configured: {result}")


async def main():
    """Run cloud connectivity examples"""
    print("=" * 60)
    print("OpenThread Border Router Manager - Cloud Connectivity Examples")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        try:
            # Note: Uncomment the connections you want to test
            # Make sure to update with your actual credentials

            # AWS IoT Core
            # await setup_aws_iot(session)

            # Azure IoT Hub
            # await setup_azure_iot(session)

            # Generic MQTT Broker
            # await setup_mqtt_broker(session)

            # For this example, we'll use a local MQTT broker
            print("\n1. Setting up local MQTT broker...")
            local_mqtt = {
                "name": "local-mqtt",
                "connection_type": "mqtt",
                "config": {
                    "broker": "localhost",
                    "port": 1883,
                    "provider": "generic_mqtt",
                    "use_tls": False
                }
            }

            async with session.post(f"{API_BASE}/cloud/connections", json=local_mqtt) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   Connected: {result}")
                else:
                    print(f"   Error: {await resp.text()}")
                    print("   Make sure Mosquitto or another MQTT broker is running on localhost:1883")
                    return

            # Start cloud manager
            await start_cloud_manager(session)

            # Manual operations
            await publish_manual_telemetry(session)
            await publish_event(session)
            await update_device_shadow(session)

            # Configuration
            await configure_intervals(session)

            # Status
            await get_cloud_status(session)
            await list_connections(session)

            print("\n" + "=" * 60)
            print("Cloud connectivity examples completed!")
            print("=" * 60)
            print("\nTips:")
            print("- Check your cloud platform console to see telemetry")
            print("- Subscribe to MQTT topics to see messages")
            print("- Send commands from cloud to control devices")

        except aiohttp.ClientError as e:
            print(f"\nError: {e}")
            print("Make sure the OT-BRM API is running on http://localhost:8000")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
