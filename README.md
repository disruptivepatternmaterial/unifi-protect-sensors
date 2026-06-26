# UniFi Protect Sensors — Home Assistant Integration

A custom Home Assistant integration that reads UniFi Protect sensor data from the
console's `/proxy/protect/api/bootstrap` REST endpoint and the `/proxy/protect/ws/updates`
WebSocket stream, exposing environmental and air-quality readings as native HA entities
that update in real time.

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
| Host | Yes | — | IP or hostname of your UniFi console |
| Port | Yes | 443 | HTTPS port |
| Username | No* | — | Local account username |
| Password | No* | — | Local account password |
| API Key | No* | — | API key from the Protect console (preferred) |
| Verify SSL | No | False | Enable to validate the console's TLS certificate |

*Either an API Key **or** Username + Password is required.

## Authentication

**API Key (recommended)**: Generate one in the Protect web UI under **System → API Keys**. The key is sent as a `Bearer` token.

**Username / Password**: The integration performs a cookie-based login to `/api/auth/login`. The `TOKEN` cookie is stored in memory and refreshed automatically on 401 responses and WebSocket auth failures.

## How Updates Work

The integration uses two data channels in parallel:

- **WebSocket (real time)** — subscribes to `/proxy/protect/ws/updates` and applies live device deltas immediately, so readings update the instant a sensor reports. Reconnects automatically with exponential backoff (2 s → 60 s cap). Session cookies are invalidated and refreshed on auth failures.
- **Bootstrap resync (every 30 seconds)** — fetches a full snapshot from `/proxy/protect/api/bootstrap` to guarantee that every sensor's `last_updated` timestamp stays current in HA even when a device is in a stable room and produces no WebSocket deltas.

## Entity Reference

See [docs/ENTITIES.md](docs/ENTITIES.md) for the full entity list with API field paths and supported device models.

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Requirements

- Home Assistant 2024.1 or later
- Python 3.11+
- No additional Python dependencies — the WebSocket client uses HA's bundled `aiohttp`.

## Development & Testing

```bash
# Run tests (no HA install required — stubs are injected automatically)
.venv_test/bin/pytest tests/ -q
```

Tests cover: helper functions, WebSocket frame decoding, deep-merge, sensor/binary-sensor descriptions, coordinator payload parsing, and entity property logic. 61 tests, no HA runtime needed.
