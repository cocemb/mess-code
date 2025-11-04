"""
OpenThread Border Router Agent Integration

This module provides integration with the OpenThread Border Router (OTBR) agent
through ot-ctl commands and REST API.
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
import subprocess
import json

logger = logging.getLogger(__name__)


class OTBRAgent:
    """
    Interface to OpenThread Border Router agent

    Communicates with OTBR through:
    - ot-ctl CLI commands
    - REST API (if available)
    - Direct socket connection
    """

    def __init__(self, ot_ctl_path: str = "/usr/bin/ot-ctl", socket_path: str = "wpan0"):
        self.ot_ctl_path = ot_ctl_path
        self.socket_path = socket_path
        self.is_connected = False

    async def connect(self) -> bool:
        """Connect to OTBR agent"""
        try:
            # Test connection with a simple command
            result = await self._run_ot_command("state")
            if result:
                self.is_connected = True
                logger.info(f"Connected to OTBR agent (state: {result})")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to OTBR agent: {e}")

        return False

    async def disconnect(self):
        """Disconnect from OTBR agent"""
        self.is_connected = False
        logger.info("Disconnected from OTBR agent")

    async def _run_ot_command(self, command: str, timeout: float = 10.0) -> Optional[str]:
        """
        Run an ot-ctl command

        Example: await _run_ot_command("state")
        """
        try:
            cmd = [self.ot_ctl_path, command]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            if process.returncode == 0:
                output = stdout.decode('utf-8').strip()
                return output
            else:
                error = stderr.decode('utf-8').strip()
                logger.error(f"ot-ctl command failed: {error}")
                return None

        except asyncio.TimeoutError:
            logger.error(f"ot-ctl command timeout: {command}")
            return None
        except Exception as e:
            logger.error(f"Error running ot-ctl command: {e}")
            return None

    # Network Management

    async def get_state(self) -> Optional[str]:
        """Get current Thread network state (disabled, detached, child, router, leader)"""
        return await self._run_ot_command("state")

    async def get_network_info(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive network information"""
        info = {}

        commands = {
            'state': 'state',
            'networkname': 'networkname',
            'panid': 'panid',
            'extpanid': 'extpanid',
            'channel': 'channel',
            'networkkey': 'networkkey',
            'version': 'version',
            'eui64': 'eui64',
            'rloc16': 'rloc16',
        }

        for key, cmd in commands.items():
            result = await self._run_ot_command(cmd)
            if result:
                info[key] = result

        return info if info else None

    async def form_network(
        self,
        network_name: str,
        panid: str,
        channel: int,
        network_key: Optional[str] = None
    ) -> bool:
        """Form a new Thread network"""
        try:
            # Set network parameters
            await self._run_ot_command(f"dataset init new")
            await self._run_ot_command(f"dataset networkname {network_name}")
            await self._run_ot_command(f"dataset panid {panid}")
            await self._run_ot_command(f"dataset channel {channel}")

            if network_key:
                await self._run_ot_command(f"dataset networkkey {network_key}")

            await self._run_ot_command(f"dataset commit active")

            # Bring up the interface
            await self._run_ot_command("ifconfig up")
            await self._run_ot_command("thread start")

            # Wait for network to form
            await asyncio.sleep(2)

            state = await self.get_state()
            logger.info(f"Network formed, state: {state}")

            return state in ['router', 'leader']

        except Exception as e:
            logger.error(f"Failed to form network: {e}")
            return False

    async def join_network(self, dataset: str) -> bool:
        """Join an existing Thread network using operational dataset"""
        try:
            await self._run_ot_command(f"dataset set active {dataset}")
            await self._run_ot_command("ifconfig up")
            await self._run_ot_command("thread start")

            # Wait for attachment
            await asyncio.sleep(3)

            state = await self.get_state()
            logger.info(f"Network join attempt, state: {state}")

            return state in ['child', 'router', 'leader']

        except Exception as e:
            logger.error(f"Failed to join network: {e}")
            return False

    async def get_dataset(self) -> Optional[str]:
        """Get active operational dataset (for sharing network credentials)"""
        result = await self._run_ot_command("dataset active -x")
        return result

    # Device Discovery and Management

    async def get_child_table(self) -> List[Dict[str, Any]]:
        """Get table of child devices"""
        result = await self._run_ot_command("child table")
        if not result:
            return []

        children = []
        # Parse output format:
        # | ID  | RLOC16 | Timeout    | Age        | LQ In | C_VN |R|D|N|Ver|CSL|QMsgCnt|
        for line in result.split('\n')[2:]:  # Skip header lines
            if '|' in line:
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 7:
                    children.append({
                        'id': parts[0],
                        'rloc16': parts[1],
                        'timeout': parts[2],
                        'age': parts[3],
                        'link_quality': parts[4],
                    })

        return children

    async def get_neighbor_table(self) -> List[Dict[str, Any]]:
        """Get table of neighbor routers"""
        result = await self._run_ot_command("neighbor table")
        if not result:
            return []

        neighbors = []
        for line in result.split('\n')[2:]:
            if '|' in line:
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 6:
                    neighbors.append({
                        'rloc16': parts[0],
                        'age': parts[1],
                        'avg_rssi': parts[2],
                        'last_rssi': parts[3],
                        'link_quality': parts[4],
                    })

        return neighbors

    async def get_router_table(self) -> List[Dict[str, Any]]:
        """Get routing table"""
        result = await self._run_ot_command("router table")
        if not result:
            return []

        routers = []
        for line in result.split('\n')[2:]:
            if '|' in line:
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 6:
                    routers.append({
                        'id': parts[0],
                        'rloc16': parts[1],
                        'next_hop': parts[2],
                        'path_cost': parts[3],
                        'link_quality_in': parts[4],
                        'link_quality_out': parts[5],
                    })

        return routers

    # Commissioner Functions (for device joining)

    async def start_commissioner(self) -> bool:
        """Start Thread Commissioner"""
        result = await self._run_ot_command("commissioner start")
        await asyncio.sleep(1)

        state = await self._run_ot_command("commissioner state")
        success = state == "active"

        if success:
            logger.info("Commissioner started")
        else:
            logger.error(f"Failed to start commissioner: {state}")

        return success

    async def stop_commissioner(self) -> bool:
        """Stop Thread Commissioner"""
        result = await self._run_ot_command("commissioner stop")
        logger.info("Commissioner stopped")
        return True

    async def add_joiner(
        self,
        eui64: str,
        pskd: str,
        timeout: int = 120
    ) -> bool:
        """
        Add a joiner device

        Args:
            eui64: Device EUI64 (use '*' for any device)
            pskd: Pre-shared key for device (PSKd)
            timeout: Join window timeout in seconds
        """
        result = await self._run_ot_command(
            f"commissioner joiner add {eui64} {pskd} {timeout}"
        )

        if result and "Done" in result:
            logger.info(f"Added joiner: {eui64}")
            return True
        else:
            logger.error(f"Failed to add joiner: {result}")
            return False

    async def remove_joiner(self, eui64: str) -> bool:
        """Remove a joiner device"""
        result = await self._run_ot_command(f"commissioner joiner remove {eui64}")
        logger.info(f"Removed joiner: {eui64}")
        return "Done" in result if result else False

    async def get_joiner_list(self) -> List[Dict[str, Any]]:
        """Get list of active joiners"""
        result = await self._run_ot_command("commissioner joiner table")
        if not result:
            return []

        joiners = []
        for line in result.split('\n'):
            # Parse joiner entries
            # Format varies, typically shows EUI64 and expiration
            if line.strip() and '|' in line:
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 2:
                    joiners.append({
                        'eui64': parts[0],
                        'expiration': parts[1] if len(parts) > 1 else None
                    })

        return joiners

    # Diagnostics

    async def ping(self, address: str, count: int = 3) -> Dict[str, Any]:
        """Ping a device on the Thread network"""
        result = await self._run_ot_command(f"ping {address} {count}")

        if not result:
            return {'success': False, 'sent': count, 'received': 0}

        # Parse ping results
        sent = count
        received = result.count("from")

        return {
            'success': received > 0,
            'sent': sent,
            'received': received,
            'loss_rate': (sent - received) / sent if sent > 0 else 1.0
        }

    async def get_counters(self) -> Optional[Dict[str, int]]:
        """Get MAC counters"""
        result = await self._run_ot_command("counters")
        if not result:
            return None

        counters = {}
        for line in result.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                try:
                    counters[key.strip()] = int(value.strip())
                except ValueError:
                    pass

        return counters

    async def reset_counters(self):
        """Reset MAC counters"""
        await self._run_ot_command("counters reset")

    async def scan_networks(self) -> List[Dict[str, Any]]:
        """Scan for available Thread networks"""
        result = await self._run_ot_command("scan", timeout=20.0)
        if not result:
            return []

        networks = []
        for line in result.split('\n'):
            if '|' in line and 'PAN' not in line:
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 7:
                    networks.append({
                        'panid': parts[0],
                        'channel': parts[1],
                        'rssi': parts[2],
                        'lqi': parts[3],
                    })

        return networks

    # Multicast

    async def subscribe_multicast(self, address: str) -> bool:
        """Subscribe to multicast address"""
        result = await self._run_ot_command(f"ipmaddr add {address}")
        return "Done" in result if result else False

    async def unsubscribe_multicast(self, address: str) -> bool:
        """Unsubscribe from multicast address"""
        result = await self._run_ot_command(f"ipmaddr del {address}")
        return "Done" in result if result else False

    async def get_multicast_addresses(self) -> List[str]:
        """Get subscribed multicast addresses"""
        result = await self._run_ot_command("ipmaddr")
        if not result:
            return []

        return [line.strip() for line in result.split('\n') if line.strip()]


# Singleton instance
otbr_agent = OTBRAgent()
