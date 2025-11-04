"""OTA Firmware update management"""

import asyncio
import hashlib
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from ..models import FirmwareVersion, FirmwareUpdate, EndDevice
from ..database import get_db_context
from ..config import settings


logger = logging.getLogger(__name__)


class FirmwareManager:
    """Manages OTA firmware updates for end devices"""

    def __init__(self):
        self.firmware_path = Path(settings.firmware_storage_path)
        self.firmware_path.mkdir(parents=True, exist_ok=True)
        self.active_updates: Dict[int, asyncio.Task] = {}

    async def register_firmware(
        self,
        version: str,
        file_path: str,
        device_types: List[str],
        description: Optional[str] = None,
        release_notes: Optional[str] = None
    ) -> FirmwareVersion:
        """Register a new firmware version"""
        # Calculate file hash
        file_hash = await self._calculate_file_hash(file_path)
        file_size = os.path.getsize(file_path)

        with get_db_context() as db:
            firmware = FirmwareVersion(
                version=version,
                file_path=file_path,
                file_hash=file_hash,
                file_size=file_size,
                description=description,
                release_notes=release_notes,
                device_types=device_types,
                is_active=True
            )
            db.add(firmware)
            db.commit()
            db.refresh(firmware)

            logger.info(f"Registered firmware version: {version}")
            return firmware

    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of firmware file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def list_firmware_versions(
        self,
        active_only: bool = True
    ) -> List[FirmwareVersion]:
        """List all firmware versions"""
        with get_db_context() as db:
            query = db.query(FirmwareVersion)
            if active_only:
                query = query.filter(FirmwareVersion.is_active == True)
            return query.order_by(FirmwareVersion.created_at.desc()).all()

    async def get_firmware_version(
        self,
        firmware_id: int
    ) -> Optional[FirmwareVersion]:
        """Get firmware version by ID"""
        with get_db_context() as db:
            return db.query(FirmwareVersion).filter(
                FirmwareVersion.id == firmware_id
            ).first()

    async def schedule_update(
        self,
        device_id: int,
        firmware_version_id: int
    ) -> FirmwareUpdate:
        """Schedule a firmware update for a device"""
        with get_db_context() as db:
            device = db.query(EndDevice).filter(EndDevice.id == device_id).first()
            if not device:
                raise ValueError(f"Device {device_id} not found")

            firmware = db.query(FirmwareVersion).filter(
                FirmwareVersion.id == firmware_version_id
            ).first()
            if not firmware:
                raise ValueError(f"Firmware version {firmware_version_id} not found")

            # Check compatibility
            if device.device_type not in firmware.device_types:
                raise ValueError(
                    f"Firmware {firmware.version} is not compatible with device type {device.device_type}"
                )

            # Create update record
            update = FirmwareUpdate(
                device_id=device_id,
                firmware_version_id=firmware_version_id,
                status="pending"
            )
            db.add(update)
            db.commit()
            db.refresh(update)

            logger.info(
                f"Scheduled firmware update for device {device.name} to version {firmware.version}"
            )
            return update

    async def schedule_bulk_updates(
        self,
        device_ids: List[int],
        firmware_version_id: int
    ) -> List[FirmwareUpdate]:
        """Schedule firmware updates for multiple devices"""
        updates = []
        for device_id in device_ids:
            try:
                update = await self.schedule_update(device_id, firmware_version_id)
                updates.append(update)
            except Exception as e:
                logger.error(f"Failed to schedule update for device {device_id}: {e}")

        logger.info(f"Scheduled {len(updates)} firmware updates")
        return updates

    async def start_update(self, update_id: int):
        """Start a firmware update"""
        with get_db_context() as db:
            update = db.query(FirmwareUpdate).filter(
                FirmwareUpdate.id == update_id
            ).first()
            if not update:
                raise ValueError(f"Update {update_id} not found")

            update.status = "in_progress"
            update.started_at = datetime.utcnow()
            db.commit()

            # Start async update task
            task = asyncio.create_task(self._perform_update(update_id))
            self.active_updates[update_id] = task

            logger.info(f"Started firmware update {update_id}")

    async def _perform_update(self, update_id: int):
        """
        Perform the actual firmware update
        This is a placeholder - real implementation would communicate with devices
        """
        try:
            with get_db_context() as db:
                update = db.query(FirmwareUpdate).filter(
                    FirmwareUpdate.id == update_id
                ).first()

                # Simulate update progress
                for progress in range(0, 101, 10):
                    await asyncio.sleep(1)  # Simulate transfer time
                    update.progress = progress
                    db.commit()

                # Mark as completed
                update.status = "completed"
                update.completed_at = datetime.utcnow()
                update.progress = 100

                # Update device firmware version
                device = update.device
                firmware = update.firmware_version
                device.firmware_version = firmware.version
                device.status = "online"

                db.commit()

                logger.info(f"Completed firmware update {update_id}")

        except Exception as e:
            logger.error(f"Firmware update {update_id} failed: {e}")
            with get_db_context() as db:
                update = db.query(FirmwareUpdate).filter(
                    FirmwareUpdate.id == update_id
                ).first()
                update.status = "failed"
                update.error_message = str(e)
                update.retry_count += 1
                db.commit()

        finally:
            if update_id in self.active_updates:
                del self.active_updates[update_id]

    async def cancel_update(self, update_id: int):
        """Cancel a pending or in-progress update"""
        with get_db_context() as db:
            update = db.query(FirmwareUpdate).filter(
                FirmwareUpdate.id == update_id
            ).first()
            if not update:
                raise ValueError(f"Update {update_id} not found")

            if update.status in ["completed", "failed"]:
                raise ValueError(f"Cannot cancel update with status: {update.status}")

            update.status = "cancelled"
            db.commit()

            # Cancel async task if running
            if update_id in self.active_updates:
                self.active_updates[update_id].cancel()
                del self.active_updates[update_id]

            logger.info(f"Cancelled firmware update {update_id}")

    async def retry_failed_update(self, update_id: int):
        """Retry a failed firmware update"""
        with get_db_context() as db:
            update = db.query(FirmwareUpdate).filter(
                FirmwareUpdate.id == update_id
            ).first()
            if not update:
                raise ValueError(f"Update {update_id} not found")

            if update.status != "failed":
                raise ValueError(f"Can only retry failed updates")

            update.status = "pending"
            update.progress = 0
            update.error_message = None
            db.commit()

            # Start update
            await self.start_update(update_id)

    async def get_update_status(self, update_id: int) -> Dict[str, Any]:
        """Get detailed update status"""
        with get_db_context() as db:
            update = db.query(FirmwareUpdate).filter(
                FirmwareUpdate.id == update_id
            ).first()
            if not update:
                raise ValueError(f"Update {update_id} not found")

            return {
                "update_id": update.id,
                "device_id": update.device_id,
                "device_name": update.device.name,
                "firmware_version": update.firmware_version.version,
                "status": update.status,
                "progress": update.progress,
                "started_at": update.started_at.isoformat() if update.started_at else None,
                "completed_at": update.completed_at.isoformat() if update.completed_at else None,
                "error_message": update.error_message,
                "retry_count": update.retry_count
            }

    async def get_device_updates(self, device_id: int) -> List[FirmwareUpdate]:
        """Get all firmware updates for a device"""
        with get_db_context() as db:
            return db.query(FirmwareUpdate).filter(
                FirmwareUpdate.device_id == device_id
            ).order_by(FirmwareUpdate.created_at.desc()).all()

    async def get_update_statistics(self) -> Dict[str, Any]:
        """Get firmware update statistics"""
        with get_db_context() as db:
            total = db.query(FirmwareUpdate).count()
            pending = db.query(FirmwareUpdate).filter(
                FirmwareUpdate.status == "pending"
            ).count()
            in_progress = db.query(FirmwareUpdate).filter(
                FirmwareUpdate.status == "in_progress"
            ).count()
            completed = db.query(FirmwareUpdate).filter(
                FirmwareUpdate.status == "completed"
            ).count()
            failed = db.query(FirmwareUpdate).filter(
                FirmwareUpdate.status == "failed"
            ).count()

            return {
                "total_updates": total,
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "failed": failed,
                "active_updates": len(self.active_updates)
            }


# Singleton instance
firmware_manager = FirmwareManager()
