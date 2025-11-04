"""
Cloud Manager - Unified cloud connectivity management

Coordinates cloud connectivity across different providers and handles:
- Automatic device telemetry publishing
- Event forwarding to cloud
- Command routing from cloud to devices
- Device shadow synchronization
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from ..database import get_db_context
from ..models import EndDevice, SensorReading
from ..core.coap_client import coap_client
from .mqtt_bridge import MQTTCloudBridge, CloudProvider
from .aws_iot import AWSIoTBridge
from .azure_iot import AzureIoTBridge

logger = logging.getLogger(__name__)


class CloudConnectionType(str, Enum):
    """Cloud connection types"""
    MQTT = "mqtt"
    AWS_IOT = "aws_iot"
    AZURE_IOT = "azure_iot"


class CloudManager:
    """
    Central cloud connectivity manager

    Manages multiple cloud connections and coordinates:
    - Telemetry publishing
    - Event publishing
    - Command handling
    - Shadow/twin synchronization
    """

    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self.is_running = False

        # Background tasks
        self._telemetry_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None

        # Configuration
        self.telemetry_interval = 60  # seconds
        self.sync_interval = 300  # seconds

    async def add_connection(
        self,
        name: str,
        connection_type: CloudConnectionType,
        config: Dict[str, Any]
    ):
        """
        Add a cloud connection

        Args:
            name: Connection name/identifier
            connection_type: Type of cloud connection
            config: Connection configuration
        """
        if connection_type == CloudConnectionType.MQTT:
            bridge = MQTTCloudBridge(
                broker=config['broker'],
                port=config.get('port', 8883),
                client_id=config.get('client_id', 'otbr-manager'),
                provider=CloudProvider(config.get('provider', 'generic_mqtt')),
                use_tls=config.get('use_tls', True),
                ca_cert=config.get('ca_cert'),
                client_cert=config.get('client_cert'),
                client_key=config.get('client_key'),
                username=config.get('username'),
                password=config.get('password')
            )

            # Register default command handlers
            self._register_default_handlers(bridge)

        elif connection_type == CloudConnectionType.AWS_IOT:
            from .aws_iot import create_aws_iot_bridge
            bridge = create_aws_iot_bridge(config)

        elif connection_type == CloudConnectionType.AZURE_IOT:
            from .azure_iot import create_azure_iot_bridge
            bridge = create_azure_iot_bridge(config)

        else:
            raise ValueError(f"Unknown connection type: {connection_type}")

        await bridge.connect()
        self.connections[name] = bridge

        logger.info(f"Added cloud connection: {name} ({connection_type})")

    async def remove_connection(self, name: str):
        """Remove a cloud connection"""
        if name in self.connections:
            bridge = self.connections[name]
            await bridge.disconnect()
            del self.connections[name]
            logger.info(f"Removed cloud connection: {name}")

    async def start(self):
        """Start cloud manager"""
        if self.is_running:
            return

        self.is_running = True

        # Start background tasks
        self._telemetry_task = asyncio.create_task(self._telemetry_loop())
        self._sync_task = asyncio.create_task(self._sync_loop())

        logger.info("Cloud manager started")

    async def stop(self):
        """Stop cloud manager"""
        self.is_running = False

        # Cancel background tasks
        if self._telemetry_task:
            self._telemetry_task.cancel()
            try:
                await self._telemetry_task
            except asyncio.CancelledError:
                pass

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Disconnect all connections
        for name in list(self.connections.keys()):
            await self.remove_connection(name)

        logger.info("Cloud manager stopped")

    async def _telemetry_loop(self):
        """Periodically publish device telemetry"""
        try:
            while self.is_running:
                await self._publish_all_telemetry()
                await asyncio.sleep(self.telemetry_interval)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in telemetry loop: {e}")

    async def _sync_loop(self):
        """Periodically sync device shadows"""
        try:
            while self.is_running:
                await self._sync_all_devices()
                await asyncio.sleep(self.sync_interval)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in sync loop: {e}")

    async def _publish_all_telemetry(self):
        """Publish telemetry for all online devices"""
        with get_db_context() as db:
            devices = db.query(EndDevice).filter(
                EndDevice.status == "online"
            ).limit(100).all()  # Batch process

            for device in devices:
                # Get latest sensor readings
                telemetry = {
                    'device_id': device.eui64,
                    'device_name': device.name,
                    'status': device.status,
                    'rssi': device.rssi,
                    'link_quality': device.link_quality,
                }

                # Add sensor data if available
                if device.sensors:
                    telemetry['sensors'] = {}
                    for sensor in device.sensors:
                        latest_reading = db.query(SensorReading).filter(
                            SensorReading.sensor_id == sensor.id
                        ).order_by(SensorReading.timestamp.desc()).first()

                        if latest_reading:
                            telemetry['sensors'][sensor.sensor_type] = {
                                'value': latest_reading.value,
                                'unit': sensor.unit,
                                'timestamp': latest_reading.timestamp.isoformat()
                            }

                # Publish to all connections
                for bridge in self.connections.values():
                    try:
                        await bridge.publish_telemetry(device.eui64, telemetry)
                    except Exception as e:
                        logger.error(f"Error publishing telemetry: {e}")

    async def _sync_all_devices(self):
        """Sync all device shadows"""
        for bridge in self.connections.values():
            if hasattr(bridge, 'sync_all_devices_to_cloud'):
                try:
                    await bridge.sync_all_devices_to_cloud()
                except Exception as e:
                    logger.error(f"Error syncing devices: {e}")

    # Event publishing

    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        connections: Optional[List[str]] = None
    ):
        """
        Publish event to cloud

        Args:
            event_type: Event type (device_joined, alarm, etc.)
            data: Event data
            connections: List of connection names (None = all)
        """
        target_bridges = self.connections.values()

        if connections:
            target_bridges = [
                self.connections[name]
                for name in connections
                if name in self.connections
            ]

        for bridge in target_bridges:
            try:
                await bridge.publish_event(event_type, data)
            except Exception as e:
                logger.error(f"Error publishing event: {e}")

    # Command handlers

    def _register_default_handlers(self, bridge):
        """Register default command handlers"""

        async def handle_read_sensor(device_id: str, data: Dict[str, Any]):
            """Read sensor value from device"""
            sensor_path = data.get('sensor_path', '/temperature')

            # Get device IPv6 address (simplified - would need actual resolution)
            # In production, maintain device address mapping
            device_address = f"fd00::{device_id[-8:]}"

            value = await coap_client.read_sensor(device_address, sensor_path)

            # Publish result back to cloud
            result = {
                'command_id': data.get('command_id'),
                'sensor': sensor_path,
                'value': value,
                'timestamp': datetime.utcnow().isoformat()
            }

            await bridge.publish_telemetry(device_id, result)

        async def handle_control_actuator(device_id: str, data: Dict[str, Any]):
            """Control actuator on device"""
            actuator_path = data.get('actuator_path', '/led')
            state = data.get('state', False)

            device_address = f"fd00::{device_id[-8:]}"

            success = await coap_client.control_actuator(
                device_address,
                actuator_path,
                state
            )

            # Publish result
            result = {
                'command_id': data.get('command_id'),
                'actuator': actuator_path,
                'state': state,
                'success': success,
                'timestamp': datetime.utcnow().isoformat()
            }

            await bridge.publish_telemetry(device_id, result)

        async def handle_get_diagnostics(device_id: str, data: Dict[str, Any]):
            """Get device diagnostics"""
            device_address = f"fd00::{device_id[-8:]}"

            diag = await coap_client.get_diagnostics(device_address)

            result = {
                'command_id': data.get('command_id'),
                'diagnostics': diag,
                'timestamp': datetime.utcnow().isoformat()
            }

            await bridge.publish_telemetry(device_id, result)

        # Register handlers
        bridge.register_command_handler('read_sensor', handle_read_sensor)
        bridge.register_command_handler('control_actuator', handle_control_actuator)
        bridge.register_command_handler('get_diagnostics', handle_get_diagnostics)

    # Manual operations

    async def publish_device_telemetry(
        self,
        device_id: str,
        data: Dict[str, Any],
        connection: Optional[str] = None
    ):
        """Manually publish telemetry for a specific device"""
        if connection:
            if connection in self.connections:
                await self.connections[connection].publish_telemetry(device_id, data)
        else:
            # Publish to all connections
            for bridge in self.connections.values():
                await bridge.publish_telemetry(device_id, data)

    async def update_device_shadow(
        self,
        device_id: str,
        reported_state: Dict[str, Any],
        connection: Optional[str] = None
    ):
        """Update device shadow"""
        if connection:
            if connection in self.connections:
                bridge = self.connections[connection]
                if hasattr(bridge, 'update_device_shadow'):
                    await bridge.update_device_shadow(device_id, reported_state)
        else:
            # Update on all connections
            for bridge in self.connections.values():
                if hasattr(bridge, 'update_device_shadow'):
                    try:
                        await bridge.update_device_shadow(device_id, reported_state)
                    except Exception as e:
                        logger.error(f"Error updating shadow: {e}")


# Singleton instance
cloud_manager = CloudManager()
