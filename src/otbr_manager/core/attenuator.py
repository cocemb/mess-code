"""External attenuator control module"""

import asyncio
import logging
import serial
import serial.tools.list_ports
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models import Attenuator
from ..database import get_db_context
from ..config import settings


logger = logging.getLogger(__name__)


class AttenuatorController:
    """Controls external RF attenuators for testing scenarios"""

    def __init__(self):
        self.connections: Dict[int, serial.Serial] = {}

    async def register_attenuator(
        self,
        name: str,
        device_path: str,
        model: str = "Generic",
        min_db: float = 0.0,
        max_db: float = 90.0
    ) -> Attenuator:
        """Register a new attenuator"""
        with get_db_context() as db:
            attenuator = Attenuator(
                name=name,
                device_path=device_path,
                model=model,
                min_attenuation_db=min_db,
                max_attenuation_db=max_db,
                current_attenuation_db=0.0,
                is_enabled=True
            )
            db.add(attenuator)
            db.commit()
            db.refresh(attenuator)

            logger.info(f"Registered attenuator: {name} at {device_path}")
            return attenuator

    async def connect_attenuator(self, attenuator_id: int):
        """Establish connection to attenuator device"""
        with get_db_context() as db:
            attenuator = db.query(Attenuator).filter(
                Attenuator.id == attenuator_id
            ).first()
            if not attenuator:
                raise ValueError(f"Attenuator {attenuator_id} not found")

            try:
                # Configure serial connection based on model
                # This is a generic implementation - specific models may need custom configs
                ser = serial.Serial(
                    port=attenuator.device_path,
                    baudrate=9600,
                    timeout=1
                )
                self.connections[attenuator_id] = ser

                logger.info(f"Connected to attenuator {attenuator.name}")

            except serial.SerialException as e:
                logger.error(f"Failed to connect to attenuator {attenuator.name}: {e}")
                raise

    async def disconnect_attenuator(self, attenuator_id: int):
        """Disconnect from attenuator device"""
        if attenuator_id in self.connections:
            self.connections[attenuator_id].close()
            del self.connections[attenuator_id]
            logger.info(f"Disconnected attenuator {attenuator_id}")

    async def set_attenuation(
        self,
        attenuator_id: int,
        attenuation_db: float
    ):
        """Set attenuation level"""
        with get_db_context() as db:
            attenuator = db.query(Attenuator).filter(
                Attenuator.id == attenuator_id
            ).first()
            if not attenuator:
                raise ValueError(f"Attenuator {attenuator_id} not found")

            if not attenuator.is_enabled:
                raise ValueError(f"Attenuator {attenuator.name} is disabled")

            # Validate range
            if attenuation_db < attenuator.min_attenuation_db or \
               attenuation_db > attenuator.max_attenuation_db:
                raise ValueError(
                    f"Attenuation {attenuation_db}dB out of range "
                    f"[{attenuator.min_attenuation_db}, {attenuator.max_attenuation_db}]"
                )

            # Send command to device
            if attenuator_id in self.connections:
                await self._send_attenuation_command(
                    attenuator_id,
                    attenuator.model,
                    attenuation_db
                )

            # Update database
            attenuator.current_attenuation_db = attenuation_db
            attenuator.updated_at = datetime.utcnow()
            db.commit()

            logger.info(
                f"Set attenuator {attenuator.name} to {attenuation_db}dB"
            )

    async def _send_attenuation_command(
        self,
        attenuator_id: int,
        model: str,
        attenuation_db: float
    ):
        """
        Send attenuation command to device
        This is model-specific - implement based on your attenuator protocol
        """
        ser = self.connections.get(attenuator_id)
        if not ser:
            raise RuntimeError(f"Attenuator {attenuator_id} not connected")

        # Generic command format (customize based on your attenuator)
        # Example: "ATT 30.5\r\n" to set 30.5dB
        command = f"ATT {attenuation_db:.1f}\r\n"

        try:
            ser.write(command.encode())
            response = ser.readline().decode().strip()

            if "OK" not in response:
                logger.warning(f"Unexpected response from attenuator: {response}")

        except Exception as e:
            logger.error(f"Failed to send command to attenuator: {e}")
            raise

    async def get_attenuation(self, attenuator_id: int) -> float:
        """Get current attenuation level"""
        with get_db_context() as db:
            attenuator = db.query(Attenuator).filter(
                Attenuator.id == attenuator_id
            ).first()
            if not attenuator:
                raise ValueError(f"Attenuator {attenuator_id} not found")

            return attenuator.current_attenuation_db

    async def create_attenuation_scenario(
        self,
        scenario_name: str,
        steps: List[Dict[str, Any]]
    ):
        """
        Create and execute an attenuation scenario
        Steps format: [{"attenuator_id": 1, "attenuation_db": 30, "duration_s": 10}, ...]
        """
        logger.info(f"Starting attenuation scenario: {scenario_name}")

        for i, step in enumerate(steps):
            attenuator_id = step["attenuator_id"]
            attenuation_db = step["attenuation_db"]
            duration_s = step.get("duration_s", 0)

            logger.info(
                f"Scenario {scenario_name} step {i+1}/{len(steps)}: "
                f"Set attenuator {attenuator_id} to {attenuation_db}dB for {duration_s}s"
            )

            await self.set_attenuation(attenuator_id, attenuation_db)

            if duration_s > 0:
                await asyncio.sleep(duration_s)

        logger.info(f"Completed attenuation scenario: {scenario_name}")

    async def assign_devices_to_attenuator(
        self,
        attenuator_id: int,
        device_ids: List[int]
    ):
        """Assign devices to be affected by this attenuator"""
        with get_db_context() as db:
            attenuator = db.query(Attenuator).filter(
                Attenuator.id == attenuator_id
            ).first()
            if not attenuator:
                raise ValueError(f"Attenuator {attenuator_id} not found")

            attenuator.affected_devices = device_ids
            db.commit()

            logger.info(
                f"Assigned {len(device_ids)} devices to attenuator {attenuator.name}"
            )

    async def list_attenuators(self) -> List[Attenuator]:
        """List all registered attenuators"""
        with get_db_context() as db:
            return db.query(Attenuator).all()

    async def get_attenuator(self, attenuator_id: int) -> Optional[Attenuator]:
        """Get attenuator by ID"""
        with get_db_context() as db:
            return db.query(Attenuator).filter(
                Attenuator.id == attenuator_id
            ).first()

    async def enable_attenuator(self, attenuator_id: int):
        """Enable an attenuator"""
        with get_db_context() as db:
            attenuator = db.query(Attenuator).filter(
                Attenuator.id == attenuator_id
            ).first()
            if not attenuator:
                raise ValueError(f"Attenuator {attenuator_id} not found")

            attenuator.is_enabled = True
            db.commit()

    async def disable_attenuator(self, attenuator_id: int):
        """Disable an attenuator"""
        with get_db_context() as db:
            attenuator = db.query(Attenuator).filter(
                Attenuator.id == attenuator_id
            ).first()
            if not attenuator:
                raise ValueError(f"Attenuator {attenuator_id} not found")

            attenuator.is_enabled = False
            db.commit()

    @staticmethod
    async def list_available_ports() -> List[str]:
        """List available serial ports for attenuator connection"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]


# Singleton instance
attenuator_controller = AttenuatorController()
