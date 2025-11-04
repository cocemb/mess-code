"""
AWS IoT Core Integration

Provides integration with AWS IoT Core using AWS IoT SDK.
Supports:
- X.509 certificate authentication
- Device shadows (Digital twins)
- Jobs for device management
- Fleet indexing
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from awscrt import mqtt
from awsiot import mqtt_connection_builder
from awsiot.iotshadow import IotShadowClient, ShadowState, UpdateShadowRequest

logger = logging.getLogger(__name__)


class AWSIoTBridge:
    """
    AWS IoT Core integration

    Uses AWS IoT SDK for optimized AWS connectivity with:
    - MQTT over TLS with X.509 certificates
    - AWS IoT Device Shadows
    - AWS IoT Jobs
    """

    def __init__(
        self,
        endpoint: str,
        client_id: str,
        cert_path: str,
        key_path: str,
        ca_path: str,
        region: str = "us-east-1"
    ):
        self.endpoint = endpoint
        self.client_id = client_id
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.region = region

        self.mqtt_connection: Optional[mqtt.Connection] = None
        self.shadow_client: Optional[IotShadowClient] = None
        self.is_connected = False

        self.message_handlers: Dict[str, Callable] = {}

    async def connect(self):
        """Connect to AWS IoT Core"""
        try:
            # Build MQTT connection
            self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
                endpoint=self.endpoint,
                cert_filepath=self.cert_path,
                pri_key_filepath=self.key_path,
                ca_filepath=self.ca_path,
                client_id=self.client_id,
                clean_session=False,
                keep_alive_secs=30
            )

            # Connect
            connect_future = self.mqtt_connection.connect()
            connect_future.result()

            self.is_connected = True

            # Create shadow client
            self.shadow_client = IotShadowClient(self.mqtt_connection)

            logger.info(f"Connected to AWS IoT Core: {self.endpoint}")

        except Exception as e:
            logger.error(f"Failed to connect to AWS IoT Core: {e}")
            raise

    async def disconnect(self):
        """Disconnect from AWS IoT Core"""
        if self.mqtt_connection:
            disconnect_future = self.mqtt_connection.disconnect()
            disconnect_future.result()

        self.is_connected = False
        logger.info("Disconnected from AWS IoT Core")

    async def publish_telemetry(
        self,
        thing_name: str,
        data: Dict[str, Any],
        qos: mqtt.QoS = mqtt.QoS.AT_LEAST_ONCE
    ):
        """
        Publish telemetry data

        Args:
            thing_name: AWS IoT Thing name
            data: Telemetry data
            qos: MQTT QoS
        """
        if not self.mqtt_connection:
            raise RuntimeError("Not connected")

        topic = f"dt/otbr/{thing_name}/telemetry"

        # Add timestamp
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()

        payload = json.dumps(data)

        publish_future, packet_id = self.mqtt_connection.publish(
            topic=topic,
            payload=payload,
            qos=qos
        )

        publish_future.result()
        logger.debug(f"Published telemetry for {thing_name}")

    async def update_shadow(
        self,
        thing_name: str,
        reported_state: Dict[str, Any]
    ):
        """
        Update device shadow

        Args:
            thing_name: AWS IoT Thing name
            reported_state: Reported device state
        """
        if not self.shadow_client:
            raise RuntimeError("Shadow client not initialized")

        request = UpdateShadowRequest(
            thing_name=thing_name,
            state=ShadowState(
                reported=reported_state
            )
        )

        future = self.shadow_client.publish_update_shadow(
            request=request,
            qos=mqtt.QoS.AT_LEAST_ONCE
        )

        future.result()
        logger.debug(f"Updated shadow for {thing_name}")

    async def subscribe_to_commands(
        self,
        thing_name: str,
        handler: Callable[[Dict[str, Any]], None]
    ):
        """
        Subscribe to commands for a thing

        Args:
            thing_name: AWS IoT Thing name
            handler: Command handler function
        """
        if not self.mqtt_connection:
            raise RuntimeError("Not connected")

        topic = f"cmd/otbr/{thing_name}/+"

        def on_message(topic, payload, dup, qos, retain, **kwargs):
            try:
                data = json.loads(payload.decode('utf-8'))
                asyncio.create_task(handler(data))
            except Exception as e:
                logger.error(f"Error handling command: {e}")

        subscribe_future, packet_id = self.mqtt_connection.subscribe(
            topic=topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_message
        )

        subscribe_future.result()
        logger.info(f"Subscribed to commands for {thing_name}")

    async def subscribe_to_shadow_delta(
        self,
        thing_name: str,
        handler: Callable[[Dict[str, Any]], None]
    ):
        """
        Subscribe to shadow delta (desired state changes)

        Args:
            thing_name: AWS IoT Thing name
            handler: Delta handler function
        """
        if not self.shadow_client:
            raise RuntimeError("Shadow client not initialized")

        def on_shadow_delta_updated(delta):
            try:
                desired = delta.state
                asyncio.create_task(handler(desired))
            except Exception as e:
                logger.error(f"Error handling shadow delta: {e}")

        subscribe_future, _ = self.shadow_client.subscribe_to_shadow_delta_updated_events(
            request={'thing_name': thing_name},
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_shadow_delta_updated
        )

        subscribe_future.result()
        logger.info(f"Subscribed to shadow delta for {thing_name}")

    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Publish system event

        Args:
            event_type: Event type
            data: Event data
        """
        if not self.mqtt_connection:
            raise RuntimeError("Not connected")

        topic = f"otbr/events/{event_type}"

        event_data = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }

        publish_future, _ = self.mqtt_connection.publish(
            topic=topic,
            payload=json.dumps(event_data),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )

        publish_future.result()


# Factory function
def create_aws_iot_bridge(config: Dict[str, str]) -> AWSIoTBridge:
    """
    Create AWS IoT Bridge from configuration

    Args:
        config: Configuration dict with keys:
            - endpoint: AWS IoT endpoint
            - client_id: Client ID
            - cert_path: Certificate file path
            - key_path: Private key file path
            - ca_path: CA certificate path
            - region: AWS region

    Returns:
        Configured AWSIoTBridge instance
    """
    return AWSIoTBridge(
        endpoint=config['endpoint'],
        client_id=config.get('client_id', 'otbr-manager'),
        cert_path=config['cert_path'],
        key_path=config['key_path'],
        ca_path=config['ca_path'],
        region=config.get('region', 'us-east-1')
    )
