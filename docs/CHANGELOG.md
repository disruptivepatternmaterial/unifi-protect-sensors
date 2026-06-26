# Changelog

All notable changes to this project will be documented here.

---

## [0.5.0] — 2026-06-25

### Added
- **Real-time WebSocket updates.** The coordinator now subscribes to the Protect
  event stream (`/proxy/protect/ws/updates`) and merges live deltas into the device
  snapshot, so battery-powered environmental sensors update the instant they report
  instead of waiting for a REST poll. This matches the behaviour of the official
  UniFi Protect integration.
- `protect_ws.py` — a dependency-free decoder for Protect's binary WebSocket frame
  format (8-byte header + JSON payload, with zlib-deflate support).
- `deep_merge()` helper for applying partial WebSocket deltas onto the snapshot.

### Changed
- Bootstrap polling is now a slow self-healing resync (every 5 minutes) rather than
  the primary data path; the WebSocket carries live data between resyncs.
- Coordinator gracefully reconnects the WebSocket with exponential backoff and
  re-authenticates on session expiry. The listener is cleanly cancelled on unload.

### Notes
- No new Python dependencies — the WebSocket client uses Home Assistant's bundled
  aiohttp session.
- Test suite expanded to 58 tests (WS frame decoding + deep-merge coverage).

---

## [0.4.0] — 2026-06-25

### Fixed
- **Root cause of all missing/ghost sensor issues**: switched the coordinator from the
  `/proxy/protect/integration/v1/sensors` endpoint (which returns no device `type` and no
  air-quality data) to `/proxy/protect/api/bootstrap` (which includes the `type` field and
  a complete `airQuality` object for every sensor).
- Corrected `expected_source` strings to match the actual device type values returned by the
  bootstrap API: `UFP-SENSE`, `USL-Environmental-US`, `USL-Entry-US`, `UP-AirQuality`.
- Fixed all UP-AirQuality payload field paths: CO₂, PM1/2.5/4/10, VOC index, AQI, and vape
  index now read from `airQuality.*` instead of the non-existent `stats.*` paths.
- Removed the `nox_index` sensor (not present in the UP-AirQuality API response).
- Fixed `vape_detected` binary sensor to use `airQuality.vape.value` instead of the
  non-existent `stats.vapeDetected` field.
- Removed the `connectivity` binary sensor (the `available` entity property already reflects
  coordinator health; the `state` field is not exposed as a binary sensor entity).
- Entity creation now uses key-existence checks (`field_exists`) for both sensors and binary
  sensors so entities are registered even when a reading is temporarily null.
- Added `field_exists()` helper to `helpers.py`.

### Changed
- `expected_source` for temperature/humidity/illuminance/battery changed from
  `USL-Environmental` → `UFP-SENSE, USL-Environmental-US` to match real device types.
- Battery sensor `expected_source` now also includes `USL-Entry-US` (door sensors have batteries).
- Test suite expanded from 32 → 46 tests; fixtures updated to match bootstrap API format.

---

## [0.3.0] — 2026-06-25

### Fixed
- Entities are now created only for descriptions whose `expected_source` matches the
  device type — eliminates ghost sensors (e.g. CO₂, AQI, vape on a USL-Environmental).
- Binary sensor creation now checks key presence in the payload rather than value
  truthiness, so null-valued fields (leakDetectedAt, tamperingDetectedAt) are
  correctly registered on supported devices.
- Coordinator now logs the device list and types at DEBUG level on every poll,
  making it easy to confirm which devices are returned by the API.

---

## [0.2.0] — 2026-06-25

### Added
- `coordinator.py` — `ProtectSensorsCoordinator` polling the `/proxy/protect/integration/v1/sensors`
  endpoint every 30 seconds. Supports both API-key auth (Bearer token) and username/password
  cookie-based auth with automatic re-authentication on 401.
- `helpers.py` — shared `get_nested(data, path)` utility for safe dot-path field traversal.
- `hacs.json` — HACS integration metadata.
- Full test suite (`tests/`) covering helpers, sensor/binary-sensor descriptions, coordinator
  payload parsing, and entity property logic. Tests use lightweight HA stubs and require no
  running Home Assistant instance.
- Fixture files for USL-Environmental and UP-AirQuality devices (`tests/fixtures/`).

### Changed
- `__init__.py` — restored; now creates and stores `ProtectSensorsCoordinator` in
  `hass.data[DOMAIN][entry.entry_id]` before forwarding platform setups. Raises
  `ConfigEntryNotReady` if the initial poll fails.
- `const.py` — restored with `DOMAIN`, `PLATFORMS`, and config key constants.
- `config_flow.py` — restored; added live credential validation during setup (tests a real
  login/API-key request before creating the entry).
- `sensor.py` — upgraded from stub to full `CoordinatorEntity`-backed implementation.
  Entities are now created unconditionally (not gated on field presence at startup) so they
  appear immediately and go to "unknown" state rather than being permanently missing if a
  field is null on first poll.
- `binary_sensor.py` — same unconditional entity creation strategy. Fixed `leak` sensor to
  use `leakDetectedAt` (nullable timestamp) instead of the incorrect `isLeakDetected` field.
- Both `sensor.py` and `binary_sensor.py` — `available` now correctly delegates to
  `super().available` (which checks `coordinator.last_update_success`) in addition to the
  device-presence check, so entities go unavailable when the NVR is unreachable.
- `manifest.json` — corrected `iot_class` from `local_push` to `local_polling`.

### Fixed
- `_get_nested` moved from `sensor.py` (private function) to `helpers.py` (public `get_nested`)
  and imported properly in `binary_sensor.py` — eliminates cross-module private symbol import.
- `coordinator.py` — replaced per-request `aiohttp.ClientSession` creation with
  `async_get_clientsession(hass)` to use the HA-managed shared session with correct lifecycle.
- `pyproject.toml` — added `requires-python = ">=3.11"` to match `target-version = "py311"`.

---

---

## [0.1.0] — 2026-06-24

### Added
- Initial HACS integration scaffold for UniFi Protect Sensors.
