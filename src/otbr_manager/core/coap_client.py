"""
CoAP Client for Thread device communication

Provides CoAP-based communication with Thread devices for:
- Resource discovery
- Sensor data reading
- Device control
- Firmware updates over CoAP
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from aiocoap import Context, Message, Code, resource
from aiocoap.numbers.contentformat import ContentFormat
import cbor2

logger = logging.getLogger(__name__)


class ThreadCoAPClient:
    """
    CoAP client for communicating with Thread devices

    Thread devices typically expose CoAP endpoints for:
    - /.well-known/core - Resource discovery
    - /temperature, /humidity - Sensor readings
    - /led, /relay - Actuator control
    - /diag - Diagnostics
    """

    def __init__(self):
        self.context: Optional[Context] = None
        self.is_initialized = False

    async def initialize(self):
        """Initialize CoAP client context"""
        if not self.is_initialized:
            self.context = await Context.create_client_context()
            self.is_initialized = True
            logger.info("CoAP client initialized")

    async def shutdown(self):
        """Shutdown CoAP client"""
        if self.context:
            await self.context.shutdown()
            self.is_initialized = False
            logger.info("CoAP client shutdown")

    async def discover_resources(self, device_address: str) -> Optional[List[Dict[str, str]]]:
        """
        Discover resources on a Thread device

        Args:
            device_address: Device IPv6 address

        Returns:
            List of resources with attributes
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            uri = f"coap://[{device_address}]/.well-known/core"
            request = Message(code=Code.GET, uri=uri)

            response = await asyncio.wait_for(
                self.context.request(request).response,
                timeout=10.0
            )

            if response.code.is_successful():
                # Parse CoRE Link Format
                # Example: </temp>;rt="temperature";if="sensor",</led>;rt="led"
                payload = response.payload.decode('utf-8')
                resources = self._parse_core_link_format(payload)

                logger.info(f"Discovered {len(resources)} resources on {device_address}")
                return resources

        except asyncio.TimeoutError:
            logger.warning(f"Timeout discovering resources on {device_address}")
        except Exception as e:
            logger.error(f"Error discovering resources: {e}")

        return None

    def _parse_core_link_format(self, link_format: str) -> List[Dict[str, str]]:
        """Parse CoRE Link Format response"""
        resources = []

        # Split by comma (between resources)
        for link in link_format.split(','):
            link = link.strip()
            if not link:
                continue

            resource = {}

            # Extract path (between < and >)
            if '<' in link and '>' in link:
                start = link.index('<') + 1
                end = link.index('>')
                resource['path'] = link[start:end]

                # Extract attributes
                attrs = link[end+1:].split(';')
                for attr in attrs:
                    if '=' in attr:
                        key, value = attr.split('=', 1)
                        key = key.strip()
                        value = value.strip(' "')
                        resource[key] = value

                resources.append(resource)

        return resources

    async def get_resource(
        self,
        device_address: str,
        path: str,
        observe: bool = False
    ) -> Optional[Any]:
        """
        GET a resource from a device

        Args:
            device_address: Device IPv6 address
            path: Resource path (e.g., "/temperature")
            observe: If True, start observing the resource

        Returns:
            Resource value
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            uri = f"coap://[{device_address}]{path}"
            request = Message(code=Code.GET, uri=uri)

            if observe:
                request.opt.observe = 0

            response = await asyncio.wait_for(
                self.context.request(request).response,
                timeout=10.0
            )

            if response.code.is_successful():
                return self._decode_payload(response)

        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting resource {path} from {device_address}")
        except Exception as e:
            logger.error(f"Error getting resource: {e}")

        return None

    async def put_resource(
        self,
        device_address: str,
        path: str,
        value: Any,
        content_format: str = "application/cbor"
    ) -> bool:
        """
        PUT/update a resource on a device

        Args:
            device_address: Device IPv6 address
            path: Resource path
            value: Value to set
            content_format: Content format

        Returns:
            True if successful
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            uri = f"coap://[{device_address}]{path}"

            # Encode payload
            if content_format == "application/cbor":
                payload = cbor2.dumps(value)
                cf = ContentFormat.CBOR
            else:
                payload = str(value).encode('utf-8')
                cf = ContentFormat.TEXT

            request = Message(
                code=Code.PUT,
                uri=uri,
                payload=payload,
                content_format=cf
            )

            response = await asyncio.wait_for(
                self.context.request(request).response,
                timeout=10.0
            )

            return response.code.is_successful()

        except Exception as e:
            logger.error(f"Error putting resource: {e}")
            return False

    async def post_resource(
        self,
        device_address: str,
        path: str,
        data: Any,
        content_format: str = "application/cbor"
    ) -> Optional[Any]:
        """POST to a resource on a device"""
        if not self.is_initialized:
            await self.initialize()

        try:
            uri = f"coap://[{device_address}]{path}"

            if content_format == "application/cbor":
                payload = cbor2.dumps(data)
                cf = ContentFormat.CBOR
            else:
                payload = str(data).encode('utf-8')
                cf = ContentFormat.TEXT

            request = Message(
                code=Code.POST,
                uri=uri,
                payload=payload,
                content_format=cf
            )

            response = await asyncio.wait_for(
                self.context.request(request).response,
                timeout=10.0
            )

            if response.code.is_successful():
                return self._decode_payload(response)

        except Exception as e:
            logger.error(f"Error posting to resource: {e}")

        return None

    def _decode_payload(self, response: Message) -> Any:
        """Decode response payload based on content format"""
        try:
            if response.opt.content_format == ContentFormat.CBOR:
                return cbor2.loads(response.payload)
            elif response.opt.content_format == ContentFormat.JSON:
                import json
                return json.loads(response.payload.decode('utf-8'))
            else:
                # Plain text
                return response.payload.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decoding payload: {e}")
            return response.payload

    # High-level device interactions

    async def read_sensor(
        self,
        device_address: str,
        sensor_path: str = "/temperature"
    ) -> Optional[float]:
        """Read sensor value from device"""
        value = await self.get_resource(device_address, sensor_path)

        if value is not None:
            try:
                # Handle different response formats
                if isinstance(value, dict):
                    return float(value.get('value', value.get('v', 0)))
                else:
                    return float(value)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse sensor value: {value}")

        return None

    async def control_actuator(
        self,
        device_address: str,
        actuator_path: str,
        state: bool
    ) -> bool:
        """Control an actuator (LED, relay, etc.)"""
        value = 1 if state else 0
        return await self.put_resource(device_address, actuator_path, value)

    async def get_diagnostics(self, device_address: str) -> Optional[Dict[str, Any]]:
        """Get device diagnostics"""
        return await self.get_resource(device_address, "/diag")

    async def ping_device(self, device_address: str) -> bool:
        """Check if device is reachable via CoAP"""
        try:
            result = await self.get_resource(device_address, "/.well-known/core")
            return result is not None
        except Exception:
            return False


# Singleton instance
coap_client = ThreadCoAPClient()
