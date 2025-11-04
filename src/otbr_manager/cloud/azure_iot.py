"""
Azure IoT Hub Integration

Provides integration with Azure IoT Hub using Azure IoT SDK.
Supports:
- Device provisioning
- Device twins
- Direct methods
- Device-to-cloud messaging
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message, MethodResponse

logger = logging.getLogger(__name__)


class AzureIoTBridge:
    """
    Azure IoT Hub integration

    Uses Azure IoT Device SDK for connectivity with:
    - MQTT/AMQP protocols
    - Device twins (digital twins)
    - Direct methods (commands)
    - Device-to-cloud messaging
    """

    def __init__(
        self,
        connection_string: str,
        device_id: str
    ):
        self.connection_string = connection_string
        self.device_id = device_id
        self.client: Optional[IoTHubDeviceClient] = None
        self.is_connected = False

        self.method_handlers: Dict[str, Callable] = {}

    async def connect(self):
        """Connect to Azure IoT Hub"""
        try:
            # Create client from connection string
            self.client = IoTHubDeviceClient.create_from_connection_string(
                self.connection_string
            )

            # Connect
            await self.client.connect()
            self.is_connected = True

            # Set up method handlers
            self.client.on_method_request_received = self._handle_method_request

            logger.info(f"Connected to Azure IoT Hub for device: {self.device_id}")

        except Exception as e:
            logger.error(f"Failed to connect to Azure IoT Hub: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Azure IoT Hub"""
        if self.client:
            await self.client.disconnect()

        self.is_connected = False
        logger.info("Disconnected from Azure IoT Hub")

    async def publish_telemetry(
        self,
        data: Dict[str, Any],
        properties: Optional[Dict[str, str]] = None
    ):
        """
        Send device-to-cloud message

        Args:
            data: Telemetry data
            properties: Optional message properties
        """
        if not self.client:
            raise RuntimeError("Not connected")

        # Add timestamp
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()

        # Create message
        message = Message(json.dumps(data))

        # Add custom properties
        if properties:
            for key, value in properties.items():
                message.custom_properties[key] = value

        # Set content type
        message.content_type = "application/json"
        message.content_encoding = "utf-8"

        # Send message
        await self.client.send_message(message)
        logger.debug(f"Sent telemetry to Azure IoT Hub")

    async def update_twin(
        self,
        reported_properties: Dict[str, Any]
    ):
        """
        Update device twin reported properties

        Args:
            reported_properties: Properties to report
        """
        if not self.client:
            raise RuntimeError("Not connected")

        await self.client.patch_twin_reported_properties(reported_properties)
        logger.debug("Updated device twin")

    async def get_twin(self) -> Dict[str, Any]:
        """Get current device twin"""
        if not self.client:
            raise RuntimeError("Not connected")

        twin = await self.client.get_twin()
        return twin

    def register_method_handler(
        self,
        method_name: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """
        Register a direct method handler

        Args:
            method_name: Method name
            handler: Async function(payload) -> response
        """
        self.method_handlers[method_name] = handler
        logger.info(f"Registered method handler: {method_name}")

    async def _handle_method_request(self, method_request):
        """Handle incoming direct method request"""
        try:
            method_name = method_request.name
            payload = method_request.payload

            logger.info(f"Received method request: {method_name}")

            if method_name in self.method_handlers:
                # Execute handler
                result = await self.method_handlers[method_name](payload)

                # Send response
                response = MethodResponse.create_from_method_request(
                    method_request,
                    status=200,
                    payload=result
                )
            else:
                # Method not found
                logger.warning(f"Unknown method: {method_name}")
                response = MethodResponse.create_from_method_request(
                    method_request,
                    status=404,
                    payload={'error': f'Method {method_name} not found'}
                )

            await self.client.send_method_response(response)

        except Exception as e:
            logger.error(f"Error handling method request: {e}")

            # Send error response
            response = MethodResponse.create_from_method_request(
                method_request,
                status=500,
                payload={'error': str(e)}
            )
            await self.client.send_method_response(response)

    async def subscribe_to_twin_desired_properties(
        self,
        handler: Callable[[Dict[str, Any]], None]
    ):
        """
        Subscribe to device twin desired property changes

        Args:
            handler: Handler function for property changes
        """
        if not self.client:
            raise RuntimeError("Not connected")

        async def on_twin_patch_received(patch):
            try:
                await handler(patch)
            except Exception as e:
                logger.error(f"Error handling twin patch: {e}")

        self.client.on_twin_desired_properties_patch_received = on_twin_patch_received
        logger.info("Subscribed to twin desired property changes")


# Factory function
def create_azure_iot_bridge(config: Dict[str, str]) -> AzureIoTBridge:
    """
    Create Azure IoT Bridge from configuration

    Args:
        config: Configuration dict with keys:
            - connection_string: Azure IoT Hub device connection string
            - device_id: Device ID

    Returns:
        Configured AzureIoTBridge instance
    """
    return AzureIoTBridge(
        connection_string=config['connection_string'],
        device_id=config.get('device_id', 'otbr-manager')
    )
