"""Database models for OT-BRM"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text,
    ForeignKey, JSON, Index, BigInteger, Enum
)
from sqlalchemy.orm import relationship
import enum

from .database import Base


class DeviceStatus(str, enum.Enum):
    """Device status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    SLEEPING = "sleeping"
    UPGRADING = "upgrading"
    ERROR = "error"


class FirmwareUpdateStatus(str, enum.Enum):
    """Firmware update status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BorderRouter(Base):
    """Border Router model"""
    __tablename__ = "border_routers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    mac_address = Column(String(17), unique=True, nullable=False)
    ip_address = Column(String(45))
    rcp_version = Column(String(50))

    # OpenThread specific
    network_name = Column(String(255))
    pan_id = Column(String(4))
    extended_pan_id = Column(String(16))
    channel = Column(Integer)
    network_key = Column(String(32))

    # Status
    status = Column(String(20), default="offline")
    last_seen = Column(DateTime, default=datetime.utcnow)

    # Topology
    topology_id = Column(Integer, ForeignKey("topologies.id"))
    topology_role = Column(String(50))  # primary, backup, mesh_node

    # Metrics
    device_count = Column(Integer, default=0)
    uptime_seconds = Column(BigInteger, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    devices = relationship("EndDevice", back_populates="border_router")
    topology = relationship("Topology", back_populates="routers")


class EndDevice(Base):
    """End Device model - optimized for scale (1000+ devices)"""
    __tablename__ = "end_devices"

    # Indexes for fast lookup on large datasets
    __table_args__ = (
        Index('idx_eui64', 'eui64'),
        Index('idx_status', 'status'),
        Index('idx_router_status', 'border_router_id', 'status'),
        Index('idx_last_seen', 'last_seen'),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Device identification
    eui64 = Column(String(16), unique=True, nullable=False, index=True)
    short_address = Column(String(4))
    name = Column(String(255))
    device_type = Column(String(50))  # router, reed, sed, med, fed

    # Network information
    border_router_id = Column(Integer, ForeignKey("border_routers.id"), index=True)
    parent_id = Column(Integer, ForeignKey("end_devices.id"))
    rloc16 = Column(String(4))

    # Status and metrics
    status = Column(String(20), default="offline", index=True)
    rssi = Column(Integer)
    link_quality = Column(Integer)
    last_seen = Column(DateTime, default=datetime.utcnow, index=True)

    # Firmware
    firmware_version = Column(String(50))

    # Capabilities
    capabilities = Column(JSON)  # Store as JSON for flexibility

    # Metadata
    metadata = Column(JSON)  # Custom fields

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    border_router = relationship("BorderRouter", back_populates="devices")
    parent = relationship("EndDevice", remote_side=[id], backref="children")
    sensors = relationship("Sensor", back_populates="device")
    firmware_updates = relationship("FirmwareUpdate", back_populates="device")


class Topology(Base):
    """Multi-router topology configuration"""
    __tablename__ = "topologies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)

    # Topology configuration
    topology_type = Column(String(50))  # star, mesh, tree, hybrid
    config = Column(JSON)  # Topology-specific configuration

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    routers = relationship("BorderRouter", back_populates="topology")


class FirmwareVersion(Base):
    """Firmware version catalog"""
    __tablename__ = "firmware_versions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False)
    file_path = Column(String(500))
    file_hash = Column(String(64))  # SHA-256
    file_size = Column(BigInteger)

    # Metadata
    description = Column(Text)
    release_notes = Column(Text)
    device_types = Column(JSON)  # List of compatible device types

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    updates = relationship("FirmwareUpdate", back_populates="firmware_version")


class FirmwareUpdate(Base):
    """Firmware update tracking"""
    __tablename__ = "firmware_updates"

    __table_args__ = (
        Index('idx_device_status', 'device_id', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(Integer, ForeignKey("end_devices.id"), nullable=False)
    firmware_version_id = Column(Integer, ForeignKey("firmware_versions.id"), nullable=False)

    # Status tracking
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)  # 0-100

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    device = relationship("EndDevice", back_populates="firmware_updates")
    firmware_version = relationship("FirmwareVersion", back_populates="updates")


class Attenuator(Base):
    """External attenuator control"""
    __tablename__ = "attenuators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    device_path = Column(String(255))

    # Configuration
    model = Column(String(100))
    min_attenuation_db = Column(Float, default=0.0)
    max_attenuation_db = Column(Float, default=90.0)
    current_attenuation_db = Column(Float, default=0.0)

    # Control
    is_enabled = Column(Boolean, default=True)

    # Associated devices
    affected_devices = Column(JSON)  # List of device IDs

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Sensor(Base):
    """Sensor registry"""
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("end_devices.id"), nullable=False)

    # Sensor info
    sensor_type = Column(String(50))  # temperature, humidity, motion, etc.
    name = Column(String(255))
    unit = Column(String(20))

    # Configuration
    sampling_interval = Column(Integer)  # seconds
    threshold_min = Column(Float)
    threshold_max = Column(Float)

    # Status
    is_active = Column(Boolean, default=True)
    last_reading_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    device = relationship("EndDevice", back_populates="sensors")
    readings = relationship("SensorReading", back_populates="sensor")


class SensorReading(Base):
    """Sensor readings - high volume table"""
    __tablename__ = "sensor_readings"

    __table_args__ = (
        Index('idx_sensor_timestamp', 'sensor_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False, index=True)

    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Optional metadata
    metadata = Column(JSON)

    # Relationships
    sensor = relationship("Sensor", back_populates="readings")
