# Testing Guide

## Running Tests

```bash
pip install homeassistant pytest pytest-asyncio
python -m pytest tests/ -v
```

## Test Coverage

### Unit tests (no HA runtime required)

`tests/test_sensor_descriptions.py` validates:
- All entity descriptions have keys and payload_field set
- No duplicate keys
- Temperature uses Celsius
- CO2 uses ppm
- PM sensors use ug/m3
- VOC, NOx, and Vape index have no unit (they are dimensionless indices)
- Leak binary sensor has MOISTURE device class
- Fixture files have the expected stats keys

### Integration tests (requires HA test environment)

Planned coverage:
- Config flow setup with valid and invalid credentials
- Entity creation per device type (USL-Environmental, UP-AirQuality)
- Availability when stats are null or missing
- Unique ID stability across restarts
- Binary sensor boolean state transitions

### Live validation

1. Install via HACS and confirm entities appear in HA
2. Verify values update via Protect websocket pushes
3. Confirm history graphs render correctly
4. Trigger water leak and tamper events; verify binary sensor state

## Adding Fixtures

See PAYLOAD_GUIDE.md for how to capture and sanitize real device payloads.
