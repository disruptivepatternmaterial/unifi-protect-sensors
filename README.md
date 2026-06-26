# UniFi Protect Sensors — Home Assistant Integration

A custom Home Assistant integration that reads UniFi Protect sensor data from the
console's `/proxy/protect/api/bootstrap` snapshot and the `/proxy/protect/ws/updates`
WebSocket stream, exposing environmental and air-quality readings as native HA entities
that update in real time.

## Supported Devices

| Model | Sensors |
|---|---|
| **UFP-SENSE / USL-Environmental-US** | Temperature, Humidity, Illuminance, Battery, Leak, Tamper, Battery Low |
| **USL-Entry-US** (door/entry) | Battery, Battery Low |
| **UP-AirQuality** | CO₂, PM1, PM2.5, PM4, PM10, VOC Index, AQI, Vape Index, Vape Detected |

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

## Updates & Polling

The integration uses two channels:

- **WebSocket (real time)** — live device deltas are streamed from
  `/proxy/protect/ws/updates` and applied immediately, so readings update the moment
  a sensor reports.
- **Bootstrap resync (every 5 minutes)** — a full snapshot is re-fetched on a slow
  interval to self-heal any missed events.

The WebSocket reconnects automatically with exponential backoff and re-authenticates
on session expiry.

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
