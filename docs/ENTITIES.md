# Entity Reference

This integration exposes the following entities for each discovered UniFi Protect sensor device.

Entities are created only for sensor/binary-sensor descriptions whose `expected_source` matches
the device's `type` field (from bootstrap) **and** whose payload path exists in the device data.
This prevents ghost entities on device types that don't support a given reading.

Data is sourced from `/proxy/protect/api/bootstrap` (full snapshot, every 30 s) and
live-patched by `/proxy/protect/ws/updates` (WebSocket push, instant on change).

---

## Sensor Entities

| Entity Key | Device Class | Unit | API Field (bootstrap path) | Supported By |
|---|---|---|---|---|
| `temperature` | `temperature` | °C | `stats.temperature.value` | UFP-SENSE, USL-Environmental-US |
| `humidity` | `humidity` | % | `stats.humidity.value` | UFP-SENSE, USL-Environmental-US |
| `illuminance` | `illuminance` | lx | `stats.light.value` | UFP-SENSE, USL-Environmental-US |
| `battery` | `battery` | % | `batteryStatus.percentage` | UFP-SENSE, USL-Environmental-US, USL-Entry-US |
| `co2` | `carbon_dioxide` | ppm | `airQuality.co2.value` | UP-AirQuality |
| `pm1` | — | µg/m³ | `airQuality.pm1p0.value` | UP-AirQuality |
| `pm25` | `pm25` | µg/m³ | `airQuality.pm2p5.value` | UP-AirQuality |
| `pm4` | — | µg/m³ | `airQuality.pm4p0.value` | UP-AirQuality |
| `pm10` | `pm10` | µg/m³ | `airQuality.pm10p0.value` | UP-AirQuality |
| `voc_index` | — | — | `airQuality.voc.value` | UP-AirQuality |
| `aqi` | `aqi` | — | `airQuality.aqi.value` | UP-AirQuality |
| `vape_index` | — | — | `airQuality.vape.value` | UP-AirQuality |

---

## Binary Sensor Entities

| Entity Key | Device Class | API Field (bootstrap path) | Notes | Supported By |
|---|---|---|---|---|
| `leak` | `moisture` | `leakDetectedAt` | `null` = clear, timestamp = active | UFP-SENSE, USL-Environmental-US |
| `battery_low` | `battery` | `batteryStatus.isLow` | Diagnostic | UFP-SENSE, USL-Environmental-US, USL-Entry-US |
| `tamper` | `tamper` | `tamperingDetectedAt` | `null` = clear, timestamp = active | UFP-SENSE, USL-Environmental-US |
| `vape_detected` | — | `airQuality.vape.value` | Non-zero value = detected | UP-AirQuality |

---

## Notes

- **Authentication**: Both API key (Bearer token) and username/password (cookie-based) are
  supported. API key is preferred. Cookies are refreshed automatically on 401 responses and
  on WebSocket handshake auth failures (401/403).
- **Update mechanism**: WebSocket push for instant updates; 30-second bootstrap resync as
  freshness floor for stable-room sensors.
- **Bootstrap endpoint**: `/proxy/protect/api/bootstrap` — the only endpoint that returns
  the device `type` field and full `airQuality` data. The integration endpoint
  `/proxy/protect/integration/v1/sensors` is **not used** (it lacks both).
- **SSL**: Verification is disabled by default because UniFi devices ship with self-signed
  certificates. Enable via the options flow if your console has a valid certificate.
- **Device model matching**: Uses the `type` field from bootstrap (e.g. `UFP-SENSE`,
  `USL-Environmental-US`, `UP-AirQuality`). Falls back to `modelKey` if `type` is absent.
