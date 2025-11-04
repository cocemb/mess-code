"""
Thread Commissioner Service

Handles device commissioning (joining) to the Thread network
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .otbr_agent import otbr_agent
from ..models import EndDevice, BorderRouter
from ..database import get_db_context


logger = logging.getLogger(__name__)


class CommissionerService:
    """
    Thread Commissioner service for device onboarding

    Manages the commissioning process:
    1. Start commissioner on border router
    2. Add joiner with credentials
    3. Wait for device to join
    4. Register device in database
    """

    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.commissioner_active = False

    async def start(self, border_router_id: int) -> bool:
        """Start commissioner service"""
        if self.commissioner_active:
            logger.warning("Commissioner already active")
            return True

        success = await otbr_agent.start_commissioner()
        if success:
            self.commissioner_active = True
            logger.info(f"Commissioner started on router {border_router_id}")

        return success

    async def stop(self) -> bool:
        """Stop commissioner service"""
        if not self.commissioner_active:
            return True

        success = await otbr_agent.stop_commissioner()
        if success:
            self.commissioner_active = False
            self.active_sessions.clear()
            logger.info("Commissioner stopped")

        return success

    async def commission_device(
        self,
        border_router_id: int,
        pskd: str,
        eui64: Optional[str] = None,
        device_name: Optional[str] = None,
        device_type: str = "sed",
        timeout: int = 120
    ) -> Optional[EndDevice]:
        """
        Commission a new device to join the network

        Args:
            border_router_id: Border router to join through
            pskd: Pre-shared key for device (PSKd/Joiner Credential)
            eui64: Device EUI64 (optional, use '*' for any device)
            device_name: Friendly name for device
            device_type: Device type (sed, med, fed, reed, router)
            timeout: Timeout in seconds

        Returns:
            EndDevice if successful, None otherwise
        """
        if not self.commissioner_active:
            logger.error("Commissioner not active, starting...")
            if not await self.start(border_router_id):
                return None

        # Use wildcard if no specific EUI64
        joiner_eui64 = eui64 or '*'

        # Add joiner to allow list
        logger.info(f"Adding joiner {joiner_eui64} with {timeout}s timeout")
        success = await otbr_agent.add_joiner(joiner_eui64, pskd, timeout)

        if not success:
            logger.error("Failed to add joiner")
            return None

        # Track session
        session_id = joiner_eui64
        self.active_sessions[session_id] = {
            'pskd': pskd,
            'eui64': joiner_eui64,
            'started_at': datetime.utcnow(),
            'timeout': timeout,
            'border_router_id': border_router_id
        }

        # Monitor for device join
        logger.info(f"Waiting for device {joiner_eui64} to join (timeout: {timeout}s)...")

        # Poll for new devices
        start_time = datetime.utcnow()
        poll_interval = 5  # seconds

        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            # Get current child table
            children = await otbr_agent.get_child_table()

            # Check if we have a new device
            for child in children:
                child_rloc16 = child.get('rloc16')

                # Check if this is a newly joined device
                # In real implementation, we'd track which devices were present before
                # For now, we'll register any device we don't have in our database
                with get_db_context() as db:
                    # Check if device exists
                    existing = db.query(EndDevice).filter(
                        EndDevice.rloc16 == child_rloc16,
                        EndDevice.border_router_id == border_router_id
                    ).first()

                    if not existing:
                        # New device joined!
                        logger.info(f"New device joined with RLOC16: {child_rloc16}")

                        # Get EUI64 if possible (would need to query device)
                        # For now, generate a temporary identifier
                        device_eui64 = eui64 if eui64 and eui64 != '*' else f"TEMP-{child_rloc16}"

                        # Register device
                        device = EndDevice(
                            eui64=device_eui64,
                            rloc16=child_rloc16,
                            border_router_id=border_router_id,
                            device_type=device_type,
                            name=device_name or f"Device-{child_rloc16}",
                            status="online",
                            link_quality=int(child.get('link_quality', 0))
                        )

                        db.add(device)
                        db.commit()
                        db.refresh(device)

                        # Clean up session
                        if session_id in self.active_sessions:
                            del self.active_sessions[session_id]

                        # Remove joiner
                        await otbr_agent.remove_joiner(joiner_eui64)

                        logger.info(f"Device commissioned successfully: {device.name}")
                        return device

            await asyncio.sleep(poll_interval)

        # Timeout reached
        logger.warning(f"Device commissioning timeout after {timeout}s")

        # Clean up
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        await otbr_agent.remove_joiner(joiner_eui64)

        return None

    async def commission_multiple_devices(
        self,
        border_router_id: int,
        devices: List[Dict[str, Any]],
        batch_timeout: int = 300
    ) -> List[EndDevice]:
        """
        Commission multiple devices in batch

        Args:
            border_router_id: Border router ID
            devices: List of device configs [{'pskd': '...', 'eui64': '...', 'name': '...'}, ...]
            batch_timeout: Total timeout for all devices

        Returns:
            List of successfully commissioned devices
        """
        if not self.commissioner_active:
            await self.start(border_router_id)

        commissioned = []

        for device_config in devices:
            try:
                device = await self.commission_device(
                    border_router_id=border_router_id,
                    pskd=device_config['pskd'],
                    eui64=device_config.get('eui64'),
                    device_name=device_config.get('name'),
                    device_type=device_config.get('device_type', 'sed'),
                    timeout=device_config.get('timeout', 120)
                )

                if device:
                    commissioned.append(device)
                    logger.info(f"Commissioned device {len(commissioned)}/{len(devices)}")

            except Exception as e:
                logger.error(f"Error commissioning device: {e}")
                continue

        logger.info(f"Commissioned {len(commissioned)}/{len(devices)} devices")
        return commissioned

    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active commissioning sessions"""
        sessions = []
        now = datetime.utcnow()

        for session_id, session in self.active_sessions.items():
            elapsed = (now - session['started_at']).total_seconds()
            remaining = max(0, session['timeout'] - elapsed)

            sessions.append({
                'session_id': session_id,
                'eui64': session['eui64'],
                'started_at': session['started_at'].isoformat(),
                'elapsed_seconds': int(elapsed),
                'remaining_seconds': int(remaining),
                'border_router_id': session['border_router_id']
            })

        return sessions

    async def cancel_session(self, eui64: str) -> bool:
        """Cancel a commissioning session"""
        if eui64 in self.active_sessions:
            await otbr_agent.remove_joiner(eui64)
            del self.active_sessions[eui64]
            logger.info(f"Cancelled commissioning session for {eui64}")
            return True

        return False


# Singleton instance
commissioner_service = CommissionerService()
