# Payload Sanitization Guide

## Why We Need Fixtures

The UP-AirQuality sensor is a newly released device. Until real JSON payloads
are captured from an actual device, payload field names for air-quality metrics
are provisional placeholders.

## How to Capture a Payload

From a machine on the same network as your UniFi console:

```bash
curl -sk -X GET \
  -H "Authorization: Bearer YOUR_API_KEY" \
  "https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/sensors" \
  | python3 -m json.tool > raw_sensors.json
```

## How to Sanitize

Replace the following before sharing:

- `"id"` -> `"DEVICE_ID_HERE"`
- `"mac"` -> `"AA:BB:CC:DD:EE:FF"`
- `"name"` -> `"Environmental Sensor"` or `"Air Quality Sensor"`
- Any `cameraId` or `bridge` references -> `"DEVICE_ID_HERE"`
- Any lat/long or location data -> remove

Keep actual stats values to confirm field names and reasonable ranges.

## Where to Put Fixtures

- `tests/fixtures/usl_environmental.json`
- `tests/fixtures/up_airquality.json`

Then open a PR or issue with the sanitized payload.
