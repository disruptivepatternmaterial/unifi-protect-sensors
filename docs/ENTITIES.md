# Entity Reference

This integration exposes the following entities for each discovered UniFi Protect sensor device.

Entities are created for every device unconditionally. Those whose corresponding API field is
absent or null for a given device type will report an **unknown** state until the field
appears in a poll response.

---

## Sensor Entities

| Entity Key | Device Class | Unit | API Field | Supported By |
|---|---|---|---|---|
| `temperature` | `temperature` | °C | `stats.temperature.value` | USL-Environmental, UP-AirQuality |
| `humidity` | `humidity` | % | `stats.humidity.value` | USL-Environmental, UP-AirQuality |
| `illuminance` | `illuminance` | lx | `stats.light.value` | USL-Environmental |
| `battery` | `battery` | % | `batteryStatus.percentage` | USL-Environmental |
| `co2` | `carbon_dioxide` | ppm | `stats.co2.value` | UP-AirQuality |
| `pm1` | — | µg/m³ | `stats.pm1.value` | UP-AirQuality |
| `pm25` | `pm25` | µg/m³ | `stats.pm25.value` | UP-AirQuality |
| `pm4` | — | µg/m³ | `stats.pm4.value` | UP-AirQuality |
| `pm10` | `pm10` | µg/m³ | `stats.pm10.value` | UP-AirQuality |
| `voc_index` | — | — | `stats.voc.value` | UP-AirQuality |
| `nox_index` | — | — | `stats.nox.value` | UP-AirQuality |
| `aqi` | `aqi` | — | `stats.aqi.value` | UP-AirQuality |
| `vape_index` | — | — | `stats.vape.value` | UP-AirQuality |

---

## Binary Sensor Entities

| Entity Key | Device Class | API Field | Notes | Supported By |
|---|---|---|---|---|
| `leak` | `moisture` | `leakDetectedAt` | Null when clear, timestamp when active | USL-Environmental |
| `battery_low` | `battery` | `batteryStatus.isLow` | Diagnostic | USL-Environmental |
| `connectivity` | `connectivity` | `isConnected` | Diagnostic | USL-Environmental, UP-AirQuality |
| `tamper` | `tamper` | `tamperingDetectedAt` | Null when clear, timestamp when active | USL-Environmental |
| `vape_detected` | — | `stats.vapeDetected` | Boolean | UP-AirQuality |

---

## Notes

- **Authentication**: Both API key (Bearer token) and username/password (cookie-based) authentication
  are supported. API key is preferred.
- **Poll interval**: 30 seconds.
- **SSL**: SSL verification is disabled by default because UniFi devices ship with self-signed
  certificates. Enable via the options flow if you have a valid certificate.
- **Device model**: Determined from the `type` field (preferred) or `modelKey` field in the
  sensor payload.
