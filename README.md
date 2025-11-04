# OpenThread Border Router Manager (OT-BRM)

A scalable, production-ready management system for OpenThread Border Routers with support for 1000+ end devices, multi-router topologies, OTA firmware updates, external attenuators, and sensor integration.

## Features

### 🌐 Border Router Management
- Register and manage multiple OpenThread Border Routers
- Real-time status monitoring and metrics
- Network configuration (PAN ID, channel, network keys)
- Support for distributed deployments

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

## API Examples

See the `examples/` directory for complete usage examples:

- `basic_usage.py` - Common operations
- `scale_test.py` - 1000+ device scale testing

## Documentation

Full API documentation available at `http://localhost:8000/docs` when running the server.

## License

MIT