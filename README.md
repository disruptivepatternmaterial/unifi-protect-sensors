# UniFi Protect Sensors — Home Assistant Integration

A custom Home Assistant integration that exposes environmental and air-quality sensor data
from UniFi Protect (UFP-SENSE, USL-Environmental, UP-AirQuality) as native HA entities,
updating in real time via the Protect WebSocket event stream.

## Why This Integration?

The official [UniFi Protect integration](https://www.home-assistant.io/integrations/unifiprotect/)
focuses on cameras, doorbells, and NVR management. Sensor devices (temperature, humidity,
air quality, leak, tamper) are supported but the sensor-specific data — particularly air
quality readings — is not always fully surfaced.

This integration is purpose-built for sensors: it connects directly to the Protect
bootstrap API and WebSocket stream, exposes every sensor reading as a properly-typed HA
entity, and works standalone without requiring the official integration to be installed.

## Supported Devices

| Model | Sensors |
|---|---|
| **UFP-SENSE** | Temperature, Humidity, Illuminance, Battery, Leak, Tamper, Battery Low |
| **USL-Environmental-US** | Temperature, Humidity, Illuminance, Battery, Leak, Tamper, Battery Low |
| **USL-Entry-US** (door/entry) | Battery, Battery Low |
| **UP-AirQuality** | Temperature, Humidity, CO₂, PM1, PM2.5, PM4, PM10, VOC Index, AQI, Vape Index, Vape Detected |

## Installation (HACS)

1. In Home Assistant, open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/disruptivepatternmaterial/unifi-protect-sensors` as type **Integration**.
3. Install **UniFi Protect Sensors** from the HACS catalogue.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** and search for **UniFi Protect Sensors**.

## Configuration

| Field | Required | Default | Description |
|---|---|---|---|
| Host | Yes | — | IP or hostname of your UniFi Protect console |
| Port | Yes | 443 | HTTPS port |
| Username | No* | — | Local account username |
| Password | No* | — | Local account password |
| API Key | No* | — | API key from the Protect console (preferred) |
| Verify SSL | No | False | Enable to validate the console's TLS certificate |

*Either an API Key **or** Username + Password is required.

> **Note**: Ubiquiti cloud/SSO accounts are not supported. Create a local account in the
> Protect web UI or generate an API key under **System → API Keys**.

## Authentication

**API Key (recommended)**: Generate one in the Protect web UI under **System → API Keys**.
The key is sent as a `Bearer` token on every request.

**Username / Password**: The integration performs a cookie-based login to `/api/auth/login`.
The session cookie is stored in memory and refreshed automatically on 401 responses and on
WebSocket auth failures.

## How Updates Work

The integration uses two data channels in parallel:

- **WebSocket (real time)** — subscribes to `/proxy/protect/ws/updates` and applies live
  device deltas immediately. Readings update the moment a sensor reports a change.
  Reconnects automatically with exponential backoff (2 s → 60 s). Auth is refreshed on
  session expiry.
- **Bootstrap resync (every 30 seconds)** — fetches a full snapshot from
  `/proxy/protect/api/bootstrap` to guarantee that every sensor's `last_updated` timestamp
  stays current in HA even when a device is in a stable room and produces no WebSocket
  deltas between polls.

## Entity Reference

See [docs/ENTITIES.md](docs/ENTITIES.md) for the full entity list with API field paths and
supported device models.

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Requirements

- Home Assistant 2024.1 or later
- Python 3.11+
- No additional Python dependencies — the WebSocket client uses HA's bundled `aiohttp`

## Development & Testing

```bash
# Create a test virtual environment (one time)
python3.11 -m venv .venv_test
.venv_test/bin/pip install pytest pytest-asyncio

# Run tests (no HA install required — stubs are injected automatically)
.venv_test/bin/pytest tests/ -q
```

Tests cover: helper functions, WebSocket frame decoding, deep-merge, sensor/binary-sensor
descriptions, coordinator payload parsing, and entity property logic. 61 tests, no live
HA instance needed.
