# UniFi Protect Sensors

A HACS-deployable Home Assistant custom integration that exposes environmental
and air-quality sensor data from UniFi Protect devices.

## Supported Devices

| Device | Entities |
|---|---|
| **USL-Environmental** | Temperature, Humidity, Ambient Light, Water Leak, Battery %, Battery Low, Connectivity, Tamper |
| **UP-AirQuality** | Temperature, Humidity, CO2, PM1, PM2.5, PM4, PM10, VOC Index, NOx Index, AQI, Vape Index, Vape Detected, Connectivity |

## Requirements

- Home Assistant 2025.1.0 or later
- UniFi Protect 7.1.0 or later (7.1.76+ recommended for UP-AirQuality)
- uiprotect 14.0.0 or later
- A local UniFi Protect user account (not a Ubiquiti cloud/SSO account)

## Installation via HACS

1. Open HACS, Integrations, three-dot menu, Custom repositories.
2. Add `https://github.com/ntableman/unifi-protect` as an Integration.
3. Search for "UniFi Protect Sensors" and install.
4. Restart Home Assistant.
5. Go to Settings, Devices and Services, Add Integration, search for "UniFi Protect Sensors".
6. Enter your Protect console host, port, local username, password, and API key.

## Manual Installation

Copy `custom_components/unifi_protect_sensors/` into your Home Assistant
`config/custom_components/` directory, then restart Home Assistant.

## Configuration

| Field | Description |
|---|---|
| Host | Local IP or hostname of your UniFi console |
| Port | Default 443 |
| Username | Local user on the console (not cloud SSO) |
| Password | Local user password |
| API Key | Generated from the console (recommended) |
| Verify SSL | Disable for self-signed certificates |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Entities appear "Unavailable" | Protect console unreachable or API key revoked |
| CO2/PM entities missing | UP-AirQuality not on Protect 7.1.76+ or different field names |
| Vape detection not working | Payload field name unconfirmed; see GitHub issues |

## Known Limitations

- Air-quality payload field names for UP-AirQuality are provisional until real
  sanitized fixtures are captured from an actual device.
- VOC index, NOx index, AQI, and vape index are unitless index values.
- UP-AirQuality is listed as "Available Jun 2026" by Ubiquiti.

## Development

```bash
python -m pytest tests/
```

See docs/TESTING.md for the full test plan.

## License

MIT
