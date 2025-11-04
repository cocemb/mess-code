# Cloud Connectivity Guide

This guide explains how to connect your OpenThread Border Router network to cloud platforms using production-ready open standards.

## Supported Cloud Platforms

- **AWS IoT Core** - Amazon's managed IoT service
- **Azure IoT Hub** - Microsoft's IoT platform
- **Google Cloud IoT** - Google's IoT service
- **Generic MQTT** - Any MQTT 3.1.1/5.0 broker

## Architecture

```
Thread Devices
      ↓
   OTBR Agent
      ↓
  OT-BRM Manager
      ↓
  Cloud Bridge (MQTT/TLS)
      ↓
Cloud Platform (AWS/Azure/Google/MQTT)
      ↓
   Your Application
```

## Features

### ✅ Telemetry Publishing
- Automatic device telemetry publishing
- Configurable intervals
- Sensor data aggregation
- Batched publishing for efficiency

### ✅ Bidirectional Communication
- Cloud → Device commands
- Device shadow/digital twin support
- Real-time command execution

### ✅ Security
- TLS 1.2/1.3 encryption
- mTLS (mutual TLS) support
- X.509 certificate authentication
- Token-based authentication

### ✅ Production Features
- Automatic reconnection
- Message queueing
- QoS levels 0, 1, 2
- Persistent sessions

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Cloud connectivity
CLOUD_ENABLED=true
CLOUD_PROVIDER=aws_iot  # or azure_iot, google_iot, mqtt
CLOUD_TELEMETRY_INTERVAL=60  # seconds
CLOUD_SYNC_INTERVAL=300  # seconds
```

## Quick Start Examples

### 1. AWS IoT Core

#### Prerequisites
1. Create IoT Thing in AWS Console
2. Download certificates:
   - Certificate (*.pem.crt)
   - Private key (*.pem.key)
   - Root CA (AmazonRootCA1.pem)
3. Create IoT Policy allowing publish/subscribe

#### Configuration

```bash
curl -X POST http://localhost:8000/api/v1/cloud/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "aws-iot",
    "connection_type": "aws_iot",
    "config": {
      "endpoint": "a3xxxxxxxxxx-ats.iot.us-east-1.amazonaws.com",
      "cert_path": "/path/to/certificate.pem.crt",
      "key_path": "/path/to/private.pem.key",
      "ca_path": "/path/to/AmazonRootCA1.pem",
      "region": "us-east-1"
    }
  }'
```

#### Start Cloud Manager

```bash
curl -X POST http://localhost:8000/api/v1/cloud/start
```

#### Subscribe to Telemetry (AWS IoT Console or MQTT client)

Subscribe to topic: `dt/otbr/+/telemetry`

### 2. Azure IoT Hub

#### Prerequisites
1. Create IoT Hub in Azure Portal
2. Register device
3. Get device connection string

#### Configuration

```bash
curl -X POST http://localhost:8000/api/v1/cloud/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "azure-iot",
    "connection_type": "azure_iot",
    "config": {
      "connection_string": "HostName=your-hub.azure-devices.net;DeviceId=otbr-manager;SharedAccessKey=xxxxx",
      "device_id": "otbr-manager"
    }
  }'
```

#### View Telemetry

Use Azure IoT Explorer or monitor the built-in Event Hub endpoint.

### 3. Generic MQTT Broker

Works with any MQTT broker (Mosquitto, HiveMQ, EMQX, etc.)

#### Configuration

```bash
curl -X POST http://localhost:8000/api/v1/cloud/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mqtt-broker",
    "connection_type": "mqtt",
    "config": {
      "broker": "mqtt.example.com",
      "port": 8883,
      "provider": "generic_mqtt",
      "use_tls": true,
      "ca_cert": "/path/to/ca.crt",
      "client_cert": "/path/to/client.crt",
      "client_key": "/path/to/client.key",
      "username": "otbr-manager",
      "password": "secret"
    }
  }'
```

## Message Formats

### Telemetry Message

Published to: `dt/otbr/{device_id}/telemetry` (generic MQTT)
           or: `devices/{device_id}/messages/events/` (Azure)
           or: `/devices/{device_id}/events` (Google)

```json
{
  "device_id": "0011223344556677",
  "device_name": "Temperature Sensor",
  "status": "online",
  "rssi": -45,
  "link_quality": 3,
  "timestamp": "2025-11-04T12:00:00Z",
  "sensors": {
    "temperature": {
      "value": 23.5,
      "unit": "°C",
      "timestamp": "2025-11-04T12:00:00Z"
    },
    "humidity": {
      "value": 45.2,
      "unit": "%",
      "timestamp": "2025-11-04T12:00:00Z"
    }
  }
}
```

### Event Message

Published to: `otbr/events/{event_type}`

```json
{
  "event_type": "device_joined",
  "timestamp": "2025-11-04T12:00:00Z",
  "data": {
    "device_id": "0011223344556677",
    "device_name": "New Sensor",
    "border_router_id": 1
  }
}
```

### Device Shadow (AWS IoT)

Topic: `$aws/things/{device_id}/shadow/update`

```json
{
  "state": {
    "reported": {
      "status": "online",
      "temperature": 23.5,
      "battery": 85
    }
  },
  "metadata": {
    "timestamp": "2025-11-04T12:00:00Z"
  }
}
```

## Sending Commands to Devices

### Command Format

Subscribe to: `cmd/otbr/{device_id}/+` (AWS)
           or: `devices/{device_id}/messages/devicebound/#` (Azure)

```json
{
  "command": "read_sensor",
  "command_id": "cmd-12345",
  "sensor_path": "/temperature"
}
```

### Supported Commands

#### Read Sensor
```json
{
  "command": "read_sensor",
  "sensor_path": "/temperature"
}
```

#### Control Actuator
```json
{
  "command": "control_actuator",
  "actuator_path": "/led",
  "state": true
}
```

#### Get Diagnostics
```json
{
  "command": "get_diagnostics"
}
```

### Response

Commands responses are published back as telemetry:

```json
{
  "command_id": "cmd-12345",
  "sensor": "/temperature",
  "value": 23.5,
  "timestamp": "2025-11-04T12:00:00Z"
}
```

## API Endpoints

### Connection Management

```bash
# Add connection
POST /api/v1/cloud/connections

# List connections
GET /api/v1/cloud/connections

# Remove connection
DELETE /api/v1/cloud/connections/{name}

# Get status
GET /api/v1/cloud/status

# Start/stop manager
POST /api/v1/cloud/start
POST /api/v1/cloud/stop
```

### Manual Operations

```bash
# Publish telemetry
POST /api/v1/cloud/telemetry/publish
{
  "device_id": "0011223344556677",
  "data": {"temperature": 23.5}
}

# Publish event
POST /api/v1/cloud/events/publish
{
  "event_type": "alarm",
  "data": {"severity": "high"}
}

# Update shadow
POST /api/v1/cloud/shadow/update
{
  "device_id": "0011223344556677",
  "reported_state": {"status": "online"}
}
```

## Advanced Configuration

### Multiple Cloud Connections

You can connect to multiple cloud platforms simultaneously:

```python
# Connect to AWS
await cloud_manager.add_connection("aws", CloudConnectionType.AWS_IOT, aws_config)

# Connect to Azure
await cloud_manager.add_connection("azure", CloudConnectionType.AZURE_IOT, azure_config)

# Connect to MQTT broker
await cloud_manager.add_connection("mqtt", CloudConnectionType.MQTT, mqtt_config)
```

### Custom Intervals

```bash
# Update telemetry interval to 30 seconds, sync to 10 minutes
curl -X PUT "http://localhost:8000/api/v1/cloud/config/intervals?telemetry_interval=30&sync_interval=600"
```

### Selective Publishing

Publish only to specific connection:

```bash
curl -X POST http://localhost:8000/api/v1/cloud/telemetry/publish \
  -d '{
    "device_id": "xxx",
    "data": {...},
    "connection": "aws-iot"
  }'
```

## Security Best Practices

### 1. Certificate Management
- Store certificates securely (not in code/env files)
- Use proper file permissions (600 for private keys)
- Rotate certificates before expiration
- Use HSM/TPM for production

### 2. Network Security
- Always use TLS (port 8883 for MQTT)
- Verify server certificates
- Use mTLS when possible
- Whitelist IPs if applicable

### 3. Access Control
- Follow principle of least privilege
- Use separate credentials per environment
- Implement device-specific policies
- Rotate secrets regularly

### 4. Data Protection
- Encrypt sensitive data in telemetry
- Use separate topics for sensitive data
- Implement data retention policies
- Log all access

## Monitoring & Troubleshooting

### Check Connection Status

```bash
curl http://localhost:8000/api/v1/cloud/status
```

### View Logs

```bash
# Docker
docker-compose logs -f api | grep -i cloud

# Native
tail -f logs/otbr_manager.log | grep -i cloud
```

### Common Issues

#### Connection Failed
- Verify certificates are valid and readable
- Check endpoint/hostname is correct
- Ensure firewall allows outbound on port 8883
- Verify credentials/policies

#### No Telemetry
- Check if cloud manager is started
- Verify devices are online
- Check telemetry interval setting
- Review cloud platform logs

#### Commands Not Working
- Verify subscription topics
- Check command format
- Ensure device is reachable via CoAP
- Review handler registrations

## Production Deployment

### Systemd Service (example)

```ini
[Unit]
Description=OT-BRM Cloud Manager
After=network.target

[Service]
Type=simple
User=otbr
WorkingDirectory=/opt/otbr-manager
ExecStart=/usr/bin/python3 -m otbr_manager.api.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker with Secrets

```yaml
services:
  api:
    environment:
      - AWS_IOT_ENDPOINT_FILE=/run/secrets/aws_endpoint
      - AWS_IOT_CERT_FILE=/run/secrets/aws_cert
      - AWS_IOT_KEY_FILE=/run/secrets/aws_key
    secrets:
      - aws_endpoint
      - aws_cert
      - aws_key

secrets:
  aws_endpoint:
    file: ./secrets/aws_endpoint.txt
  aws_cert:
    file: ./secrets/certificate.pem.crt
  aws_key:
    file: ./secrets/private.pem.key
```

## References

- [AWS IoT Core Documentation](https://docs.aws.amazon.com/iot/)
- [Azure IoT Hub Documentation](https://docs.microsoft.com/azure/iot-hub/)
- [MQTT v3.1.1 Specification](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/)
- [MQTT v5.0 Specification](https://docs.oasis-open.org/mqtt/mqtt/v5.0/)
