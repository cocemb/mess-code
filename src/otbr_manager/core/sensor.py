"""Sensor integration and monitoring system"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..models import Sensor, SensorReading, EndDevice
from ..database import get_db_context


logger = logging.getLogger(__name__)


class SensorManager:
    """Manages sensors and their readings"""

    def __init__(self):
        self.active_monitors: Dict[int, asyncio.Task] = {}

    async def register_sensor(
        self,
        device_id: int,
        sensor_type: str,
        name: str,
        unit: str,
        sampling_interval: int = 60,
        threshold_min: Optional[float] = None,
        threshold_max: Optional[float] = None
    ) -> Sensor:
        """Register a new sensor"""
        with get_db_context() as db:
            device = db.query(EndDevice).filter(EndDevice.id == device_id).first()
            if not device:
                raise ValueError(f"Device {device_id} not found")

            sensor = Sensor(
                device_id=device_id,
                sensor_type=sensor_type,
                name=name,
                unit=unit,
                sampling_interval=sampling_interval,
                threshold_min=threshold_min,
                threshold_max=threshold_max,
                is_active=True
            )
            db.add(sensor)
            db.commit()
            db.refresh(sensor)

            logger.info(
                f"Registered sensor: {name} ({sensor_type}) for device {device.name}"
            )
            return sensor

    async def get_sensor(self, sensor_id: int) -> Optional[Sensor]:
        """Get sensor by ID"""
        with get_db_context() as db:
            return db.query(Sensor).filter(Sensor.id == sensor_id).first()

    async def list_sensors(
        self,
        device_id: Optional[int] = None,
        sensor_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Sensor]:
        """List sensors with optional filters"""
        with get_db_context() as db:
            query = db.query(Sensor)

            if device_id:
                query = query.filter(Sensor.device_id == device_id)
            if sensor_type:
                query = query.filter(Sensor.sensor_type == sensor_type)
            if active_only:
                query = query.filter(Sensor.is_active == True)

            return query.all()

    async def record_reading(
        self,
        sensor_id: int,
        value: float,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SensorReading:
        """Record a sensor reading"""
        with get_db_context() as db:
            sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
            if not sensor:
                raise ValueError(f"Sensor {sensor_id} not found")

            reading = SensorReading(
                sensor_id=sensor_id,
                value=value,
                timestamp=timestamp or datetime.utcnow(),
                metadata=metadata
            )
            db.add(reading)

            # Update sensor's last reading time
            sensor.last_reading_at = reading.timestamp

            db.commit()
            db.refresh(reading)

            # Check thresholds and log alerts
            await self._check_thresholds(sensor, value)

            return reading

    async def _check_thresholds(self, sensor: Sensor, value: float):
        """Check if reading is outside threshold and log alert"""
        alerts = []

        if sensor.threshold_min is not None and value < sensor.threshold_min:
            alerts.append(
                f"Sensor {sensor.name} reading {value}{sensor.unit} "
                f"below minimum threshold {sensor.threshold_min}{sensor.unit}"
            )

        if sensor.threshold_max is not None and value > sensor.threshold_max:
            alerts.append(
                f"Sensor {sensor.name} reading {value}{sensor.unit} "
                f"above maximum threshold {sensor.threshold_max}{sensor.unit}"
            )

        for alert in alerts:
            logger.warning(alert)

    async def bulk_record_readings(
        self,
        readings: List[Dict[str, Any]]
    ) -> int:
        """Bulk record multiple sensor readings for efficiency"""
        with get_db_context() as db:
            count = 0

            for reading_data in readings:
                sensor_id = reading_data['sensor_id']
                value = reading_data['value']
                timestamp = reading_data.get('timestamp', datetime.utcnow())
                metadata = reading_data.get('metadata')

                reading = SensorReading(
                    sensor_id=sensor_id,
                    value=value,
                    timestamp=timestamp,
                    metadata=metadata
                )
                db.add(reading)
                count += 1

            db.commit()
            logger.info(f"Bulk recorded {count} sensor readings")

            return count

    async def get_readings(
        self,
        sensor_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[SensorReading]:
        """Get sensor readings with time range filter"""
        with get_db_context() as db:
            query = db.query(SensorReading).filter(
                SensorReading.sensor_id == sensor_id
            )

            if start_time:
                query = query.filter(SensorReading.timestamp >= start_time)
            if end_time:
                query = query.filter(SensorReading.timestamp <= end_time)

            return query.order_by(
                SensorReading.timestamp.desc()
            ).limit(limit).all()

    async def get_latest_reading(self, sensor_id: int) -> Optional[SensorReading]:
        """Get the most recent reading for a sensor"""
        with get_db_context() as db:
            return db.query(SensorReading).filter(
                SensorReading.sensor_id == sensor_id
            ).order_by(SensorReading.timestamp.desc()).first()

    async def get_sensor_statistics(
        self,
        sensor_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get statistical summary of sensor readings"""
        with get_db_context() as db:
            query = db.query(SensorReading).filter(
                SensorReading.sensor_id == sensor_id
            )

            if start_time:
                query = query.filter(SensorReading.timestamp >= start_time)
            if end_time:
                query = query.filter(SensorReading.timestamp <= end_time)

            # Calculate statistics
            stats = db.query(
                func.count(SensorReading.id).label('count'),
                func.avg(SensorReading.value).label('avg'),
                func.min(SensorReading.value).label('min'),
                func.max(SensorReading.value).label('max')
            ).filter(
                SensorReading.sensor_id == sensor_id
            )

            if start_time:
                stats = stats.filter(SensorReading.timestamp >= start_time)
            if end_time:
                stats = stats.filter(SensorReading.timestamp <= end_time)

            result = stats.first()

            sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()

            return {
                "sensor_id": sensor_id,
                "sensor_name": sensor.name if sensor else None,
                "sensor_type": sensor.sensor_type if sensor else None,
                "unit": sensor.unit if sensor else None,
                "count": result.count or 0,
                "average": round(result.avg, 2) if result.avg else None,
                "minimum": result.min,
                "maximum": result.max,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            }

    async def get_aggregated_readings(
        self,
        sensor_id: int,
        interval_minutes: int = 60,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get time-series aggregated readings (avg per interval)
        Useful for charting and reducing data volume
        """
        # This is a simplified version - production would use proper time bucketing
        with get_db_context() as db:
            query = db.query(SensorReading).filter(
                SensorReading.sensor_id == sensor_id
            )

            if start_time:
                query = query.filter(SensorReading.timestamp >= start_time)
            if end_time:
                query = query.filter(SensorReading.timestamp <= end_time)

            readings = query.order_by(SensorReading.timestamp).all()

            # Group by interval
            aggregated = []
            if not readings:
                return aggregated

            current_bucket = []
            bucket_start = readings[0].timestamp

            for reading in readings:
                if (reading.timestamp - bucket_start).total_seconds() >= interval_minutes * 60:
                    # Finish current bucket
                    if current_bucket:
                        avg_value = sum(r.value for r in current_bucket) / len(current_bucket)
                        aggregated.append({
                            "timestamp": bucket_start.isoformat(),
                            "value": round(avg_value, 2),
                            "count": len(current_bucket)
                        })

                    # Start new bucket
                    current_bucket = [reading]
                    bucket_start = reading.timestamp
                else:
                    current_bucket.append(reading)

            # Add final bucket
            if current_bucket:
                avg_value = sum(r.value for r in current_bucket) / len(current_bucket)
                aggregated.append({
                    "timestamp": bucket_start.isoformat(),
                    "value": round(avg_value, 2),
                    "count": len(current_bucket)
                })

            return aggregated

    async def delete_old_readings(
        self,
        days_to_keep: int = 30
    ) -> int:
        """Delete old sensor readings to manage database size"""
        with get_db_context() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            deleted = db.query(SensorReading).filter(
                SensorReading.timestamp < cutoff_date
            ).delete()

            db.commit()

            logger.info(f"Deleted {deleted} old sensor readings (older than {days_to_keep} days)")
            return deleted

    async def update_sensor_config(
        self,
        sensor_id: int,
        sampling_interval: Optional[int] = None,
        threshold_min: Optional[float] = None,
        threshold_max: Optional[float] = None
    ):
        """Update sensor configuration"""
        with get_db_context() as db:
            sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
            if not sensor:
                raise ValueError(f"Sensor {sensor_id} not found")

            if sampling_interval is not None:
                sensor.sampling_interval = sampling_interval
            if threshold_min is not None:
                sensor.threshold_min = threshold_min
            if threshold_max is not None:
                sensor.threshold_max = threshold_max

            db.commit()

    async def delete_sensor(self, sensor_id: int):
        """Delete a sensor"""
        with get_db_context() as db:
            sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
            if not sensor:
                raise ValueError(f"Sensor {sensor_id} not found")

            db.delete(sensor)
            db.commit()

            logger.info(f"Deleted sensor: {sensor.name}")


# Singleton instance
sensor_manager = SensorManager()
