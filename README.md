# OpenThread Border Router Manager (OT-BRM)

A scalable, production-ready management system for OpenThread Border Routers with support for 1000+ end devices, multi-router topologies, OTA firmware updates, external attenuators, and sensor integration.

## Features

### 🔗 OpenThread Integration
- **OTBR Agent Integration**: Direct integration with OpenThread Border Router via `ot-ctl`
- **Thread Commissioner**: Device commissioning and joining
- **CoAP Client**: Device communication over CoAP protocol
- **mDNS Discovery**: Automatic device and service discovery
- **Network Management**: Form, join, and manage Thread networks
- **Device Diagnostics**: Ping, neighbor tables, router tables

### 🌐 Border Router Management
- Register and manage multiple OpenThread Border Routers
- Real-time status monitoring and metrics
- Network configuration (PAN ID, channel, network keys)
- Support for distributed deployments
- Automatic connection to OTBR agent

### 📱 End Device Management (Scale: 1000+)
- Efficient device registration and tracking
- Bulk operations for large-scale deployments
- Device search and filtering
- Hierarchical network tree visualization
- Parent-child relationship tracking
- Stale device detection

### 🔀 Multi-Router Topologies
- **Star Topology**: Primary router with backup failover
- **Mesh Topology**: Fully connected router mesh
- **Tree Topology**: Hierarchical router structure
- **Custom Topologies**: Flexible configuration options
- Topology visualization and management

### 🔄 OTA Firmware Updates
- Centralized firmware version management
- Individual and bulk device updates
- Update progress tracking
- Automatic retry on failure
- Version compatibility checks
- Update scheduling and queuing

### 📡 External Attenuator Control
- RF attenuator integration for testing
- Programmable attenuation scenarios
- Device-specific attenuation assignment
- Multiple attenuator support
- Serial device auto-discovery

### 📊 Sensor Integration
- Multi-sensor type support (temperature, humidity, motion, etc.)
- High-volume data ingestion
- Real-time threshold monitoring and alerts
- Time-series data aggregation
- Statistical analysis
- Automatic data retention management

### 🚀 REST API
- Comprehensive RESTful API
- OpenAPI/Swagger documentation
- Pagination for large datasets
- Bulk operations support
- Real-time status updates
- Commissioner API for device joining
- Network diagnostics endpoints

## Prerequisites

### OpenThread Border Router Setup

OT-BRM requires an OpenThread Border Router (OTBR) to be installed and running. See [docs/OTBR_SETUP.md](docs/OTBR_SETUP.md) for detailed setup instructions.

Quick OTBR setup:
```bash
# Install OTBR (on Raspberry Pi or Linux)
git clone https://github.com/openthread/ot-br-posix.git
cd ot-br-posix
./script/bootstrap
./script/setup
```

## Quick Start

### Using Docker (Recommended)

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

The API will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

**Note**: Docker container needs access to OTBR. Either:
1. Run OTBR on host and expose socket to container
2. Run OTBR in the same Docker network
3. Use `--network host` mode (Linux only)

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Initialize database
python -c "from src.otbr_manager.database import init_db; init_db()"

# Run API server
python -m uvicorn src.otbr_manager.api.main:app --host 0.0.0.0 --port 8000
```

## Usage Examples

### Commission a Device to Join Network

```bash
# Start commissioner
curl -X POST http://localhost:8000/api/v1/commissioning/start \
  -H "Content-Type: application/json" \
  -d '{"border_router_id": 1}'

# Add device (put device in pairing mode first)
curl -X POST http://localhost:8000/api/v1/commissioning/commission \
  -H "Content-Type: application/json" \
  -d '{
    "border_router_id": 1,
    "pskd": "J01NME",
    "device_name": "Temperature Sensor",
    "device_type": "sed",
    "timeout": 120
  }'
```

### Get Network Topology

```bash
# Get child devices
curl http://localhost:8000/api/v1/commissioning/network/children

# Get neighbor routers
curl http://localhost:8000/api/v1/commissioning/network/neighbors

# Get network info
curl http://localhost:8000/api/v1/commissioning/network/info
```

### Device Communication

```python
from otbr_manager.core.coap_client import coap_client

# Initialize
await coap_client.initialize()

# Read sensor
temperature = await coap_client.read_sensor("fd00::1234", "/temperature")

# Control LED
await coap_client.control_actuator("fd00::1234", "/led", True)
```

## Example Scripts

See the `examples/` directory for complete usage examples:

- `basic_usage.py` - Common operations
- `scale_test.py` - 1000+ device scale testing

## Documentation

- **API Documentation**: `http://localhost:8000/docs` (when running)
- **OTBR Setup Guide**: [docs/OTBR_SETUP.md](docs/OTBR_SETUP.md)
- **Architecture**: See below

## Architecture

```
┌─────────────────────────────────────────────┐
│         OT-BRM Application                  │
│  ┌────────────────────────────────────────┐ │
│  │      REST API (FastAPI)                │ │
│  └────────────┬───────────────────────────┘ │
│               │                              │
│  ┌────────────┴───────────────────────────┐ │
│  │  Commissioner │ CoAP │ mDNS Discovery  │ │
│  └────────────┬───────────────────────────┘ │
│               │                              │
│  ┌────────────┴───────────────────────────┐ │
│  │     OTBR Agent (ot-ctl interface)      │ │
│  └────────────┬───────────────────────────┘ │
└───────────────┼──────────────────────────────┘
                │
┌───────────────┼──────────────────────────────┐
│  OpenThread Border Router (OTBR)            │
│               │                              │
│  ┌────────────┴───────────────────────────┐ │
│  │    otbr-agent + Spinel Protocol        │ │
│  └────────────┬───────────────────────────┘ │
└───────────────┼──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│     OpenThread RCP (nRF52840, etc.)         │
└──────────────────────────────────────────────┘
```

## License

MIT