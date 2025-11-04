"""
mDNS/DNS-SD Discovery for Thread Devices

Discovers Thread devices advertising services via mDNS
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser, AsyncServiceInfo
from zeroconf import ServiceStateChange

logger = logging.getLogger(__name__)


class ThreadDeviceDiscovery:
    """
    Discover Thread devices using mDNS/DNS-SD

    Thread Border Routers typically advertise:
    - _meshcop._udp.local. - Thread Mesh Commissioning
    - _otbr._tcp.local. - OpenThread Border Router
    """

    # Service types to monitor
    SERVICE_TYPES = [
        "_meshcop._udp.local.",  # Thread MeshCoP
        "_otbr._tcp.local.",      # OpenThread BR
        "_coap._udp.local.",      # CoAP devices
    ]

    def __init__(self):
        self.aiozc: Optional[AsyncZeroconf] = None
        self.browsers: List[AsyncServiceBrowser] = []
        self.discovered_devices: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        self.callbacks: List[Callable] = []

    async def start(self):
        """Start mDNS discovery"""
        if self.is_running:
            logger.warning("Discovery already running")
            return

        try:
            self.aiozc = AsyncZeroconf()

            # Create browsers for each service type
            for service_type in self.SERVICE_TYPES:
                browser = AsyncServiceBrowser(
                    self.aiozc.zeroconf,
                    service_type,
                    handlers=[self._on_service_state_change]
                )
                self.browsers.append(browser)

            self.is_running = True
            logger.info(f"mDNS discovery started, monitoring {len(self.SERVICE_TYPES)} service types")

        except Exception as e:
            logger.error(f"Failed to start mDNS discovery: {e}")
            raise

    async def stop(self):
        """Stop mDNS discovery"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel browsers
        for browser in self.browsers:
            await browser.async_cancel()

        self.browsers.clear()

        # Close zeroconf
        if self.aiozc:
            await self.aiozc.async_close()

        logger.info("mDNS discovery stopped")

    def _on_service_state_change(
        self,
        zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange
    ):
        """Handle service state changes"""
        asyncio.create_task(
            self._handle_service_change(zeroconf, service_type, name, state_change)
        )

    async def _handle_service_change(
        self,
        zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange
    ):
        """Handle service state change asynchronously"""
        try:
            if state_change is ServiceStateChange.Added:
                await self._on_service_added(zeroconf, service_type, name)
            elif state_change is ServiceStateChange.Removed:
                await self._on_service_removed(name)
            elif state_change is ServiceStateChange.Updated:
                await self._on_service_updated(zeroconf, service_type, name)

        except Exception as e:
            logger.error(f"Error handling service change: {e}")

    async def _on_service_added(self, zeroconf, service_type: str, name: str):
        """Handle new service discovered"""
        logger.info(f"Discovered service: {name}")

        # Get service info
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)

        if info:
            device_info = self._extract_device_info(info, service_type)
            self.discovered_devices[name] = device_info

            logger.info(f"Device info: {device_info}")

            # Notify callbacks
            for callback in self.callbacks:
                try:
                    await callback('added', device_info)
                except Exception as e:
                    logger.error(f"Error in discovery callback: {e}")

    async def _on_service_removed(self, name: str):
        """Handle service removed"""
        if name in self.discovered_devices:
            device_info = self.discovered_devices.pop(name)
            logger.info(f"Device removed: {name}")

            # Notify callbacks
            for callback in self.callbacks:
                try:
                    await callback('removed', device_info)
                except Exception as e:
                    logger.error(f"Error in discovery callback: {e}")

    async def _on_service_updated(self, zeroconf, service_type: str, name: str):
        """Handle service updated"""
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)

        if info:
            device_info = self._extract_device_info(info, service_type)
            self.discovered_devices[name] = device_info

            logger.info(f"Device updated: {name}")

            # Notify callbacks
            for callback in self.callbacks:
                try:
                    await callback('updated', device_info)
                except Exception as e:
                    logger.error(f"Error in discovery callback: {e}")

    def _extract_device_info(
        self,
        info: AsyncServiceInfo,
        service_type: str
    ) -> Dict[str, Any]:
        """Extract device information from service info"""
        # Get addresses
        addresses = []
        if info.parsed_addresses():
            addresses = list(info.parsed_addresses())

        # Get TXT record properties
        properties = {}
        if info.properties:
            for key, value in info.properties.items():
                try:
                    properties[key.decode('utf-8')] = value.decode('utf-8')
                except:
                    properties[key.decode('utf-8')] = value.hex()

        device_info = {
            'name': info.name,
            'type': service_type,
            'addresses': addresses,
            'port': info.port,
            'properties': properties,
            'server': info.server,
        }

        # Extract Thread-specific info
        if service_type == "_meshcop._udp.local.":
            # Thread Commissioner/Joiner info
            device_info['role'] = 'thread_device'
            if 'nn' in properties:  # Network Name
                device_info['network_name'] = properties['nn']
            if 'xp' in properties:  # Extended PAN ID
                device_info['extended_panid'] = properties['xp']

        elif service_type == "_otbr._tcp.local.":
            # Border Router info
            device_info['role'] = 'border_router'

        elif service_type == "_coap._udp.local.":
            # CoAP device
            device_info['role'] = 'coap_device'

        return device_info

    def register_callback(self, callback: Callable):
        """
        Register a callback for device discovery events

        Callback signature: async def callback(event: str, device_info: dict)
        Events: 'added', 'removed', 'updated'
        """
        self.callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """Unregister a callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def get_discovered_devices(
        self,
        service_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of discovered devices"""
        devices = list(self.discovered_devices.values())

        if service_type:
            devices = [d for d in devices if d['type'] == service_type]

        return devices

    def get_border_routers(self) -> List[Dict[str, Any]]:
        """Get discovered border routers"""
        return [
            d for d in self.discovered_devices.values()
            if d.get('role') == 'border_router'
        ]

    def get_thread_devices(self) -> List[Dict[str, Any]]:
        """Get discovered Thread devices"""
        return [
            d for d in self.discovered_devices.values()
            if d.get('role') == 'thread_device'
        ]


# Singleton instance
mdns_discovery = ThreadDeviceDiscovery()
