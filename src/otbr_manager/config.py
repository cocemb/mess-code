"""Configuration management for OT-BRM"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = Field(default="sqlite:///./otbr_manager.db")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_reload: bool = Field(default=False)

    # OpenThread
    ot_rcp_device: str = Field(default="/dev/ttyACM0")
    ot_backbone_interface: str = Field(default="eth0")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Firmware
    firmware_storage_path: str = Field(default="./firmware")
    max_firmware_size_mb: int = Field(default=50)

    # Attenuator
    attenuator_enabled: bool = Field(default=True)
    attenuator_device: str = Field(default="/dev/ttyUSB0")
    attenuator_range_db: str = Field(default="0-90")

    # Monitoring
    metrics_enabled: bool = Field(default=True)
    log_level: str = Field(default="INFO")

    # Security
    api_key: str = Field(default="change-this-key")
    jwt_secret: str = Field(default="change-this-secret")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
