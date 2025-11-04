"""
Cloud Bridge - MQTT-based cloud connectivity

Provides production-ready cloud integration using MQTT with support for:
- AWS IoT Core
- Azure IoT Hub
- Google Cloud IoT
- Generic MQTT brokers
- TLS/mTLS authentication
- Bidirectional communication
"""

import asyncio
import logging
import json
import ssl
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from enum import Enum
import aiomqtt

from ..database import get_db_context
from ..models import EndDevice, BorderRouter
from .device_manager import device_manager


logger = logging.getLogger(__name__)


class CloudProvider(str, Enum):
    """Supported cloud providers"""
    AWS_IOT = "aws_iot"
    AZURE_IOT = "azure_iot"
    GOOGLE_IOT = "google_iot"
    GENERIC_MQTT = "generic_mqtt"


class MQTTCloudBridge:
    """
    MQTT-based cloud bridge for Thread network

    Publishes telemetry and receives commands via MQTT.
    Supports major cloud IoT platforms with proper authentication.
    """

    def __init__(
        self,
        broker: str,
        port: int = 8883,
        client_id: str = "otbr-manager",
        provider: CloudProvider = CloudProvider.GENERIC_MQTT,
        use_tls: bool = True,
        ca_cert: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.provider = provider
        self.use_tls = use_tls

        # TLS configuration
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key

        # Authentication
        self.username = username
        self.password = password

        # MQTT client
        self.client: Optional[aiomqtt.Client] = None
        self.is_connected = False

        # Message handlers
        self.command_handlers: Dict[str, Callable] = {}

        # Publishing queues
        self.telemetry_queue: asyncio.Queue = asyncio.Queue()
        self.event_queue: asyncio.Queue = asyncio.Queue()

        # Background tasks
        self._publish_task: Optional[asyncio.Task] = None
        self._subscribe_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Connect to MQTT broker"""
        try:
            # Configure TLS
            tls_params = None
            if self.use_tls:
                tls_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

                if self.ca_cert:
                    tls_context.load_verify_locations(self.ca_cert)

                if self.client_cert and self.client_key:
                    tls_context.load_cert_chain(
                        certfile=self.client_cert,
                        keyfile=self.client_key
                    )

                tls_params = aiomqtt.TLSParameters(
                    context=tls_context
                )

            # Create MQTT client
            self.client = aiomqtt.Client(
                hostname=self.broker,
                port=self.port,
                client_id=self.client_id,
                username=self.username,
                password=self.password,
                tls_params=tls_params,
                clean_session=False,  # Persistent session
                keepalive=60
            )

            await self.client.__aenter__()
            self.is_connected = True

            logger.info(f"Connected to MQTT broker: {self.broker}:{self.port} ({self.provider})")

            # Start background tasks
            self._publish_task = asyncio.create_task(self._publish_loop())
            self._subscribe_task = asyncio.create_task(self._subscribe_loop())

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MQTT broker"""
        self.is_connected = False

        # Cancel background tasks
        if self._publish_task:
            self._publish_task.cancel()
            try:
                await self._publish_task
            except asyncio.CancelledError:
                pass

        if self._subscribe_task:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass

        # Disconnect client
        if self.client:
            await self.client.__aexit__(None, None, None)

        logger.info("Disconnected from MQTT broker")

    # Topic naming based on provider

    def _get_telemetry_topic(self, device_id: str) -> str:
        """Get telemetry topic for device"""
        if self.provider == CloudProvider.AWS_IOT:
            return f"dt/otbr/{device_id}/telemetry"
        elif self.provider == CloudProvider.AZURE_IOT:
            return f"devices/{device_id}/messages/events/"
        elif self.provider == CloudProvider.GOOGLE_IOT:
            return f"/devices/{device_id}/events"
        else:  # Generic MQTT
            return f"otbr/devices/{device_id}/telemetry"

    def _get_command_topic(self, device_id: str) -> str:
        """Get command topic for device"""
        if self.provider == CloudProvider.AWS_IOT:
            return f"cmd/otbr/{device_id}/#"
        elif self.provider == CloudProvider.AZURE_IOT:
            return f"devices/{device_id}/messages/devicebound/#"
        elif self.provider == CloudProvider.GOOGLE_IOT:
            return f"/devices/{device_id}/commands/#"
        else:  # Generic MQTT
            return f"otbr/devices/{device_id}/commands/#"

    def _get_shadow_topic(self, device_id: str, suffix: str) -> str:
        """Get device shadow topic"""
        if self.provider == CloudProvider.AWS_IOT:
            return f"$aws/things/{device_id}/shadow/{suffix}"
        else:
            return f"otbr/devices/{device_id}/shadow/{suffix}"

    # Publishing

    async def publish_telemetry(
        self,
        device_id: str,
        data: Dict[str, Any],
        qos: int = 1
    ):
        """
        Publish device telemetry to cloud

        Args:
            device_id: Device identifier
            data: Telemetry data
            qos: MQTT QoS level (0, 1, or 2)
        """
        topic = self._get_telemetry_topic(device_id)

        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()

        await self.telemetry_queue.put({
            'topic': topic,
            'payload': json.dumps(data),
            'qos': qos
        })

    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        qos: int = 1
    ):
        """
        Publish system event to cloud

        Args:
            event_type: Event type (device_joined, device_left, alarm, etc.)
            data: Event data
            qos: MQTT QoS level
        """
        topic = f"otbr/events/{event_type}"

        event_data = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }

        await self.event_queue.put({
            'topic': topic,
            'payload': json.dumps(event_data),
            'qos': qos
        })

    async def update_device_shadow(
        self,
        device_id: str,
        reported_state: Dict[str, Any]
    ):
        """
        Update device shadow/digital twin

        Args:
            device_id: Device identifier
            reported_state: Current device state
        """
        topic = self._get_shadow_topic(device_id, "update")

        shadow_update = {
            'state': {
                'reported': reported_state
            },
            'metadata': {
                'timestamp': datetime.utcnow().isoformat()
            }
        }

        if self.client:
            await self.client.publish(
                topic,
                payload=json.dumps(shadow_update),
                qos=1
            )

    async def _publish_loop(self):
        """Background task to publish queued messages"""
        try:
            while self.is_connected:
                # Process telemetry queue
                try:
                    msg = await asyncio.wait_for(
                        self.telemetry_queue.get(),
                        timeout=1.0
                    )

                    if self.client:
                        await self.client.publish(
                            msg['topic'],
                            payload=msg['payload'],
                            qos=msg['qos']
                        )
                        logger.debug(f"Published telemetry to {msg['topic']}")

                except asyncio.TimeoutError:
                    pass

                # Process event queue
                try:
                    msg = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=0.1
                    )

                    if self.client:
                        await self.client.publish(
                            msg['topic'],
                            payload=msg['payload'],
                            qos=msg['qos']
                        )
                        logger.debug(f"Published event to {msg['topic']}")

                except asyncio.TimeoutError:
                    pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in publish loop: {e}")

    # Subscribing and command handling

    async def subscribe_to_commands(self, device_ids: List[str]):
        """Subscribe to command topics for devices"""
        if not self.client:
            raise RuntimeError("Not connected to MQTT broker")

        for device_id in device_ids:
            topic = self._get_command_topic(device_id)
            await self.client.subscribe(topic)
            logger.info(f"Subscribed to commands for device {device_id}")

    async def subscribe_to_shadow_updates(self, device_ids: List[str]):
        """Subscribe to shadow update topics"""
        if not self.client:
            raise RuntimeError("Not connected to MQTT broker")

        for device_id in device_ids:
            # Subscribe to desired state updates
            topic = self._get_shadow_topic(device_id, "update/delta")
            await self.client.subscribe(topic)

    async def _subscribe_loop(self):
        """Background task to handle incoming messages"""
        try:
            if not self.client:
                return

            async for message in self.client.messages:
                await self._handle_message(message)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in subscribe loop: {e}")

    async def _handle_message(self, message):
        """Handle incoming MQTT message"""
        try:
            topic = str(message.topic)
            payload = message.payload.decode('utf-8')

            logger.info(f"Received message on {topic}")

            # Parse payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON payload: {payload}")
                return

            # Route to appropriate handler
            if 'commands' in topic or 'devicebound' in topic:
                await self._handle_command(topic, data)
            elif 'shadow' in topic:
                await self._handle_shadow_update(topic, data)
            else:
                logger.warning(f"Unhandled topic: {topic}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _handle_command(self, topic: str, data: Dict[str, Any]):
        """Handle device command from cloud"""
        # Extract device ID from topic
        # Format depends on provider
        parts = topic.split('/')

        if self.provider == CloudProvider.AWS_IOT:
            device_id = parts[2] if len(parts) > 2 else None
        elif self.provider == CloudProvider.AZURE_IOT:
            device_id = parts[1] if len(parts) > 1 else None
        else:
            device_id = parts[2] if len(parts) > 2 else None

        if not device_id:
            logger.warning(f"Could not extract device ID from topic: {topic}")
            return

        command_type = data.get('command') or data.get('method')

        if command_type in self.command_handlers:
            try:
                await self.command_handlers[command_type](device_id, data)
            except Exception as e:
                logger.error(f"Error executing command {command_type}: {e}")
        else:
            logger.warning(f"Unknown command: {command_type}")

    async def _handle_shadow_update(self, topic: str, data: Dict[str, Any]):
        """Handle device shadow update from cloud"""
        logger.info(f"Shadow update: {data}")

        # Extract desired state
        desired = data.get('state', {}).get('desired', {})

        if desired:
            # Update device state
            # This would trigger actual device control via CoAP
            logger.info(f"Applying desired state: {desired}")

    # Command handlers

    def register_command_handler(
        self,
        command_type: str,
        handler: Callable[[str, Dict[str, Any]], Any]
    ):
        """
        Register a command handler

        Args:
            command_type: Command type identifier
            handler: Async function(device_id, data) -> result
        """
        self.command_handlers[command_type] = handler
        logger.info(f"Registered command handler: {command_type}")

    # Bulk operations

    async def publish_bulk_telemetry(self, telemetry_data: List[Dict[str, Any]]):
        """Publish telemetry for multiple devices"""
        for item in telemetry_data:
            device_id = item.get('device_id')
            data = item.get('data', {})

            if device_id:
                await self.publish_telemetry(device_id, data)

    async def sync_all_devices_to_cloud(self):
        """Sync all devices to cloud (publish current state)"""
        with get_db_context() as db:
            devices = db.query(EndDevice).filter(
                EndDevice.status == "online"
            ).all()

            for device in devices:
                state = {
                    'device_id': device.eui64,
                    'name': device.name,
                    'type': device.device_type,
                    'status': device.status,
                    'rssi': device.rssi,
                    'link_quality': device.link_quality,
                    'firmware_version': device.firmware_version,
                    'last_seen': device.last_seen.isoformat() if device.last_seen else None
                }

                await self.update_device_shadow(device.eui64, state)

            logger.info(f"Synced {len(devices)} devices to cloud")


# Singleton instance
mqtt_bridge = MQTTCloudBridge(
    broker="localhost",  # Will be configured from settings
    port=1883,
    provider=CloudProvider.GENERIC_MQTT
)
