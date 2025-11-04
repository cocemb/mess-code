"""Main FastAPI application"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from ..database import init_db
from ..config import settings
from .routes import routers, devices, topologies, firmware, attenuators, sensors, commissioning
from ..core.otbr_agent import otbr_agent
from ..core.mdns_discovery import mdns_discovery


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup
    logger.info("Starting OT-BRM API...")
    init_db()
    logger.info("Database initialized")

    # Connect to OTBR agent
    try:
        await otbr_agent.connect()
        logger.info("Connected to OTBR agent")
    except Exception as e:
        logger.warning(f"Could not connect to OTBR agent: {e}")

    # Start mDNS discovery
    try:
        await mdns_discovery.start()
        logger.info("mDNS discovery started")
    except Exception as e:
        logger.warning(f"Could not start mDNS discovery: {e}")

    yield

    # Shutdown
    logger.info("Shutting down OT-BRM API...")

    # Stop mDNS discovery
    try:
        await mdns_discovery.stop()
    except Exception:
        pass

    # Disconnect from OTBR
    try:
        await otbr_agent.disconnect()
    except Exception:
        pass


# Create FastAPI app
app = FastAPI(
    title="OpenThread Border Router Manager",
    description="Scalable management system for OpenThread Border Routers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "otbr-manager"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OpenThread Border Router Manager API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(routers.router, prefix="/api/v1/routers", tags=["Border Routers"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["End Devices"])
app.include_router(topologies.router, prefix="/api/v1/topologies", tags=["Topologies"])
app.include_router(firmware.router, prefix="/api/v1/firmware", tags=["Firmware"])
app.include_router(attenuators.router, prefix="/api/v1/attenuators", tags=["Attenuators"])
app.include_router(sensors.router, prefix="/api/v1/sensors", tags=["Sensors"])
app.include_router(commissioning.router, prefix="/api/v1/commissioning", tags=["Commissioning"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "otbr_manager.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
