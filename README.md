# UniFi Protect Sensors — Home Assistant Integration

A custom Home Assistant integration that polls the UniFi Protect `/proxy/protect/integration/v1/sensors` endpoint and exposes environmental and air-quality sensor data as native HA entities.

## Supported Devices

| Model | Sensors |
|---|---|
| **USL-Environmental** | Temperature, Humidity, Illuminance, Battery, Leak, Tamper, Connectivity, Battery Low |
| **UP-AirQuality** | Temperature, Humidity, CO₂, PM1, PM2.5, PM4, PM10, VOC Index, NOx Index, AQI, Vape Index, Vape Detected, Connectivity |

## Installation (HACS)

1. In Home Assistant, open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/disruptivepatternmaterial/unifi-protect-sensors` as type **Integration**.
3. Install **UniFi Protect Sensors** from the HACS catalogue.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** and search for **UniFi Protect Sensors**.

## Configuration

| Field | Required | Default | Description |
|---|---|---|---|
| Host | Yes | — | IP or hostname of your UniFi console |
| Port | Yes | 443 | HTTPS port |
| Username | No* | — | Local account username |
| Password | No* | — | Local account password |
| API Key | No* | — | API key from the Protect console (preferred) |
| Verify SSL | No | False | Enable to validate the console's TLS certificate |

*Either an API Key **or** Username + Password is required.

## Authentication

**API Key (recommended)**: Generate one in the Protect web UI under **System → API Keys**. The key is sent as a `Bearer` token.

**Username / Password**: The integration performs a cookie-based login to `/api/auth/login`. The `TOKEN` cookie is stored in memory and refreshed automatically on 401 responses.

## Poll Interval

Sensor data is fetched every **30 seconds** (`local_polling` class).

## Entity Reference

See [docs/ENTITIES.md](docs/ENTITIES.md) for the full entity list with API field paths and supported device models.

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Requirements

- Home Assistant 2024.1 or later
- Python 3.11+
- `uiprotect >= 14.0.0` (listed as `after_dependencies` — not directly used but ensures the UniFi Protect integration is set up first)

## Development & Testing

```bash
# Run tests (no HA install required — stubs are injected automatically)
python -m pytest tests/ -v
```

Tests cover: helper functions, sensor/binary-sensor description structure, coordinator payload parsing, and entity property logic.
