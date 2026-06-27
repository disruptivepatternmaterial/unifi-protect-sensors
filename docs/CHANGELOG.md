# Changelog

All notable changes to this project will be documented here.

---

## [0.5.4] — 2026-06-26

### Fixed
- **`aq_temperature` and `aq_humidity` showed raw key names in HA UI** — translation
  strings were missing for the two sensors added in v0.5.3. Both now display as
  "Temperature" and "Humidity" respectively.
- **Dead translation strings removed** — `nox_index` and `connectivity` entries were
  still present in `strings.json` and `translations/en.json` despite those entities
  being removed in v0.4.0.

### Changed
- `iot_class` corrected from `local_polling` to `local_push` in `manifest.json` — the
  integration uses a WebSocket push stream as its primary data path.
- README updated: added "Why this integration?" section explaining the relationship to
  the official UniFi Protect integration; added venv setup instructions for development.
- CHANGELOG v0.5.0 entry clarified to note that the 5-minute bootstrap interval was
  revised to 30 seconds in v0.5.1.

---

## [0.5.3] — 2026-06-26

### Fixed
- **Missing Temperature and Humidity on UP-AirQuality** — the device exposes these
  readings in `airQuality.temperature` and `airQuality.humidity` (not `stats.*`),
  but no sensor descriptions existed for those paths. Two new descriptions added:
  `aq_temperature` and `aq_humidity` with `expected_source="UP-AirQuality"`.

---

## [0.5.2] — 2026-06-26

### Fixed (adversarial review findings)
- **Reconnect busy-loop on server-initiated WS close**: `_ws_connect_and_listen`
  now raises `ConnectionError` whenever the connection ends (normal or abnormal),
  so `_ws_loop` always applies exponential backoff before reconnecting. Previously
  a graceful server close reset backoff to zero, causing a hot reconnect loop.
- **Stale session cookie after WS auth failure**: `WSServerHandshakeError` with
  status 401/403 now clears `_session_cookie` before backing off, so the next
  reconnect triggers a fresh login instead of retrying a dead token indefinitely.
- **Unbounded `zlib` decompression (memory amplification)**: Frame decompression
  now uses `zlib.decompressobj` with a 10 MB cap and raises `ValueError` if the
  limit is exceeded, preventing memory/CPU amplification from malicious frames.
- **Frame `packet_type` not validated**: `decode_ws_message` now asserts that
  frame 1 is an action frame (type 1) and frame 2 is a data frame (type 2),
  rejecting out-of-order or malformed frame sequences.
- **WS cursor stale after reconnect**: `_last_update_id` is now advanced from
  `newUpdateId` for *all* model types before the `modelKey == "sensor"` filter,
  so non-sensor frames no longer leave the cursor behind on reconnect.
- WS message type comparisons switched from fragile `msg.type.name` strings to
  `aiohttp.WSMsgType` enum constants.

### Changed
- 61 tests passing (up from 58); new tests cover frame type validation, zlib size
  cap, and type-wrong-order rejection.

---

## [0.5.1] — 2026-06-26

### Fixed
- **Sensors in stable rooms never refreshed in HA** — `async_set_updated_data`
  (used for WebSocket updates) resets the coordinator's scheduled resync timer
  each time it's called. With the AQ sensor sending WS messages every ~30 s,
  the 5-minute bootstrap resync never actually ran, so any sensor that hadn't
  received a WS delta since startup had a permanently stale `last_updated`
  timestamp in HA.
- Fixed by switching WS updates to mutate `self.data` in place and call
  `async_update_listeners()` directly, which notifies entity callbacks without
  touching the schedule.
- Bootstrap interval restored to **30 seconds** (matching original behaviour)
  so every sensor's `last_updated` stays fresh in HA even in stable rooms.

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
- Bootstrap polling initially set to 5 minutes as the self-healing resync interval
  (revised to 30 seconds in v0.5.1 — see below).
- Coordinator gracefully reconnects the WebSocket with exponential backoff and
  re-authenticates on session expiry. The listener is cancelled cleanly on unload.

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

## [0.1.0] — 2026-06-24

### Added
- Initial HACS integration scaffold for UniFi Protect Sensors.
