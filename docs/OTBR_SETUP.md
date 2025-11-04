# OpenThread Border Router (OTBR) Setup Guide

This guide explains how to set up and integrate OpenThread Border Router with OT-BRM.

## Prerequisites

### Hardware Requirements
- Raspberry Pi 4 (recommended) or similar Linux device
- OpenThread RCP device (e.g., nRF52840 USB Dongle, Nordic nRF52840 DK)
- Network connectivity (Ethernet or Wi-Fi)

### Software Requirements
- Ubuntu 20.04+ or Raspberry Pi OS
- Docker (optional, for containerized deployment)

## Installing OTBR

### Option 1: Official OTBR Installation

```bash
# Clone OpenThread Border Router repository
git clone https://github.com/openthread/ot-br-posix.git
cd ot-br-posix

# Run installation script
./script/bootstrap
./script/setup

# Configure with your RCP device
sudo systemctl enable otbr-agent
sudo systemctl start otbr-agent
```

### Option 2: Docker Installation

```bash
# Pull OTBR Docker image
docker pull openthread/otbr:latest

# Run OTBR container
docker run -d --name otbr \
  --sysctl net.ipv6.conf.all.disable_ipv6=0 \
  --privileged \
  --network host \
  -v /dev/ttyACM0:/dev/ttyACM0 \
  openthread/otbr \
  --radio-url spinel+hdlc+uart:///dev/ttyACM0
```

## Verifying OTBR Installation

```bash
# Check OTBR agent status
sudo systemctl status otbr-agent

# Test ot-ctl connection
sudo ot-ctl state
# Should output: disabled, detached, or connected state

# Check available commands
sudo ot-ctl help
```

## Forming a Thread Network

### Using ot-ctl

```bash
# Initialize new network dataset
sudo ot-ctl dataset init new
sudo ot-ctl dataset networkname "MyThreadNetwork"
sudo ot-ctl dataset panid 0x1234
sudo ot-ctl dataset channel 15
sudo ot-ctl dataset commit active

# Bring up network interface
sudo ot-ctl ifconfig up
sudo ot-ctl thread start

# Check status
sudo ot-ctl state
# Should be: leader or router

# Get network credentials (to share with other devices)
sudo ot-ctl dataset active -x
```

### Using OT-BRM API

```bash
# Form network via API
curl -X POST http://localhost:8000/api/v1/routers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BR-Main",
    "mac_address": "00:11:22:33:44:55",
    "ip_address": "192.168.1.100",
    "rcp_version": "1.0.0",
    "network_name": "MyThreadNetwork",
    "pan_id": "1234",
    "channel": 15
  }'
```

## Commissioning Devices

### Method 1: Using Commissioner API

```bash
# Start commissioner
curl -X POST http://localhost:8000/api/v1/commissioning/start \
  -H "Content-Type: application/json" \
  -d '{"border_router_id": 1}'

# Commission a device (device must be in pairing mode)
curl -X POST http://localhost:8000/api/v1/commissioning/commission \
  -H "Content-Type: application/json" \
  -d '{
    "border_router_id": 1,
    "pskd": "J01NME",
    "device_name": "My Sensor",
    "device_type": "sed",
    "timeout": 120
  }'
```

### Method 2: Using ot-ctl

```bash
# Start commissioner
sudo ot-ctl commissioner start

# Add joiner (use device's EUI64 or * for any)
sudo ot-ctl commissioner joiner add * J01NME 120

# On the joining device (if you have CLI access):
# ifconfig up
# joiner start J01NME
```

## Device Communication

### Discovering Devices

```bash
# Get child table (direct children of this border router)
curl http://localhost:8000/api/v1/commissioning/network/children

# Get neighbor table (routers)
curl http://localhost:8000/api/v1/commissioning/network/neighbors

# Get full network info
curl http://localhost:8000/api/v1/commissioning/network/info
```

### CoAP Communication

Devices on Thread network typically use CoAP for communication:

```python
from otbr_manager.core.coap_client import coap_client

# Initialize CoAP client
await coap_client.initialize()

# Discover device resources
resources = await coap_client.discover_resources("fd00::1234")

# Read sensor value
temperature = await coap_client.read_sensor("fd00::1234", "/temperature")

# Control actuator
success = await coap_client.control_actuator("fd00::1234", "/led", True)
```

## Network Diagnostics

### Using ot-ctl

```bash
# Check network state
sudo ot-ctl state

# View routing table
sudo ot-ctl router table

# View child devices
sudo ot-ctl child table

# Ping a device
sudo ot-ctl ping fd00::1234

# Get network dataset
sudo ot-ctl dataset active

# Scan for networks
sudo ot-ctl scan
```

### Using API

```bash
# Ping a device
curl -X POST "http://localhost:8000/api/v1/commissioning/network/ping?address=fd00::1234&count=3"

# Scan networks
curl http://localhost:8000/api/v1/commissioning/network/scan

# Get statistics
curl http://localhost:8000/api/v1/devices/statistics
```

## Troubleshooting

### OTBR Not Starting

```bash
# Check logs
sudo journalctl -u otbr-agent -f

# Verify RCP device is connected
ls /dev/ttyACM*

# Check permissions
sudo usermod -a -G dialout $USER
```

### Commissioner Not Working

```bash
# Verify commissioner state
sudo ot-ctl commissioner state

# Check if network is formed
sudo ot-ctl state
# Must be in 'leader' or 'router' state

# Restart OTBR agent
sudo systemctl restart otbr-agent
```

### Devices Not Joining

1. Verify device is in commissioning mode
2. Check PSKd/joiner credential is correct
3. Ensure commissioner is active
4. Check device is within RF range
5. Verify network channel matches device capability

```bash
# View active joiners
sudo ot-ctl commissioner joiner table

# Check logs for join attempts
sudo journalctl -u otbr-agent | grep -i joiner
```

### CoAP Communication Issues

```bash
# Ping device first
sudo ot-ctl ping fd00::1234

# Check device IPv6 addresses
sudo ot-ctl ipaddr

# Verify multicast subscription
sudo ot-ctl ipmaddr
```

## Integration with OT-BRM

### Configuration

Update `.env` file:

```bash
# OTBR Configuration
OT_RCP_DEVICE=/dev/ttyACM0
OT_BACKBONE_INTERFACE=eth0
```

### Architecture

```
┌─────────────────────────────────────────┐
│         OT-BRM Application              │
│  ┌───────────────────────────────────┐  │
│  │      FastAPI REST API             │  │
│  └───────────┬───────────────────────┘  │
│              │                           │
│  ┌───────────┴───────────────────────┐  │
│  │   Commissioner Service            │  │
│  │   CoAP Client                     │  │
│  │   mDNS Discovery                  │  │
│  └───────────┬───────────────────────┘  │
│              │                           │
│  ┌───────────┴───────────────────────┐  │
│  │   OTBR Agent Interface            │  │
│  │   (ot-ctl commands)               │  │
│  └───────────┬───────────────────────┘  │
└──────────────┼───────────────────────────┘
               │
┌──────────────┴───────────────────────────┐
│     OpenThread Border Router (OTBR)      │
│  ┌────────────────────────────────────┐  │
│  │        otbr-agent                  │  │
│  │        otbr-web                    │  │
│  └────────────┬───────────────────────┘  │
│               │                           │
│  ┌────────────┴───────────────────────┐  │
│  │     Spinel Protocol                │  │
│  └────────────┬───────────────────────┘  │
└───────────────┼───────────────────────────┘
                │
┌───────────────┴───────────────────────────┐
│      OpenThread RCP Device                │
│      (nRF52840, etc.)                     │
└───────────────────────────────────────────┘
```

## Best Practices

1. **Security**
   - Use unique network keys for each deployment
   - Rotate commissioner credentials regularly
   - Use device-specific PSKd (not wildcard) in production

2. **Scalability**
   - Enable router role on capable devices
   - Distribute load across multiple border routers
   - Monitor network partition count

3. **Reliability**
   - Implement device heartbeat monitoring
   - Use redundant border routers
   - Enable auto-rejoin on devices

4. **Performance**
   - Optimize CoAP poll intervals
   - Use multicast for group operations
   - Implement CoAP observe for subscriptions

## References

- [OpenThread Border Router GitHub](https://github.com/openthread/ot-br-posix)
- [OpenThread Documentation](https://openthread.io/)
- [Thread Specification](https://www.threadgroup.org/)
- [CoAP RFC 7252](https://tools.ietf.org/html/rfc7252)
