# Changelog

All notable changes to this project will be documented here.

---

## [0.7.0] — 2026-09-07

### Security

- **Local operator tooling is no longer published with the integration** — a
  maintainer-only agent-skill file holding deployment host details was removed
  from version control, and `.cursor/` is now ignored so it cannot return.
- **A real device MAC address was published in a test fixture** —
  `tests/fixtures/up_airquality.json` now uses the documentation placeholder
  `AABBCCDDEEFF`, matching the guidance already in `docs/PAYLOAD_GUIDE.md`
  ([#1](https://github.com/disruptivepatternmaterial/unifi-protect-sensors/issues/1)).

### Added

- **Reauthentication flow** — when the console rejects the stored credentials,
  Home Assistant now prompts for a new API key or password instead of leaving
  the integration retrying a dead credential every 30 seconds. Previously the
  only way to change credentials was to delete and re-add the integration.
- **Continuous integration** — every push and pull request now runs ruff,
  the test suite, Home Assistant `hassfest`, and HACS validation. None of these
  ran automatically before, so a broken commit could be tagged and released.

### Fixed

- **Devices with no name registered as `None`** — Protect reports `name: null`
  for a device that has never been named, and that null was passed straight to
  the device registry. Such devices now fall back to their device id.
- **Wrong credentials retried forever** — a rejected password or API key raised
  a generic update failure, so the coordinator kept polling with a credential
  the console had already refused. Both now raise `ConfigEntryAuthFailed` and
  trigger the new reauth flow.
- **Blank credentials reported "invalid username or password"** — submitting the
  config form with no API key and no password sent an empty login to the console
  and surfaced its rejection. The form now reports that credentials are missing.
- **A late session invalidation could discard a fresh login** — a 401 arriving
  after a concurrent reconnect had already re-authenticated would clear the new
  cookie, forcing another login. Invalidation now only clears the exact session
  that was rejected, and is a no-op for API-key auth, which has no session.
- **Shutdown swallowed real errors** — cancelling the WebSocket listener caught
  and discarded every exception, including bugs in the listener. Cancellation is
  now the only silently-accepted outcome; anything else is logged.
- **A binary sensor reported "clear" for a device that had vanished** — a device
  missing from the snapshot now reports unknown rather than fabricating an
  off state.

### Changed

- **Entity plumbing shared between platforms** — `sensor.py` and
  `binary_sensor.py` each carried their own copy of device discovery, device
  registry creation, availability and coordinator wiring. That logic now lives
  once in `entity.py`; the platform modules only declare which readings they
  expose. Device entries are created from each entity's `DeviceInfo` instead of
  a hand-rolled device-registry pass.
- **Device models are a typed list, not a comma-separated string** — entity
  descriptions declare `device_types=(MODEL_UP_AIRQUALITY,)` using named
  constants and are matched with `description.supports(...)`, replacing runtime
  splitting of a `"UFP-SENSE, USL-Environmental-US"` string.
- **The config flow is now covered by tests.** It could not even be imported
  under the test stubs, so a syntax or name error in the module that gates setup
  would only have been discovered by a user whose integration failed to load.

## [0.6.0] — 2026-06-29

### Fixed
- **Options flow `verify_ssl` had no effect** — the coordinator only read
  `entry.data`, while the options flow wrote `entry.options`, and no reload
  listener was registered. Options are now merged over data and the entry is
  reloaded when options change, so toggling SSL verification actually applies.
- **Background WebSocket task could leak** — if platform setup failed after the
  first refresh, the WS task kept running. The coordinator is now linked to the
  config entry and torn down if setup fails.
- **Stale session not recovered on HTTP 403** — only 401 cleared the session
  cookie; consoles that return 403 for a dead token now also trigger re-auth.
- **API-key validation hit the wrong endpoint** — the config flow validated
  `/proxy/protect/integration/v1/sensors` but the coordinator polls
  `/proxy/protect/api/bootstrap`; validation now uses the same bootstrap
  endpoint so a mis-scoped key is rejected at setup.
- **Device-type matching false positives** — the bidirectional substring filter
  could match a short type against a longer model name (and a blank type against
  everything). Replaced with an exact, case-insensitive match.
- **Leak/tamper showed "unknown" while clear** — `leakDetectedAt` /
  `tamperingDetectedAt` are null when no event is active (a definitive clear
  state), so those binary sensors now report off instead of unknown, fixing
  `to: 'off'` automations and history.
- **Requests could stall for minutes** — login, bootstrap, and the WebSocket
  handshake are now bounded by a 10-second timeout instead of relying on the
  shared session's ~5-minute default.
- **WebSocket reconnect backoff never recovered** — backoff now resets after a
  connection has been stable, so a few early blips no longer pin reconnects at
  the 60-second maximum.
- **`pm1` and `pm4` had no device class** — both now use the proper
  `SensorDeviceClass.PM1` / `PM4`, matching `pm25` / `pm10`.
- **Two consoles on one host could not both be added** — the config-entry unique
  id now includes the port (`host:port`); existing entries are migrated
  automatically (config entry v1 -> v2).
- **Hardening** — login is serialized to avoid duplicate sessions; the WebSocket
  decoder rejects truncated/malformed compressed frames; config-flow validation
  only swallows network errors; a narrow WebSocket connection leak on handshake
  timeout was closed.

- **Offline devices now show unavailable** — entities go unavailable when their
  device reports `state: DISCONNECTED` instead of showing stale values.

### Added
- **Newly adopted sensors appear automatically** — entity discovery now re-runs
  on every coordinator update, so devices/fields that show up after startup get
  entities without reloading the integration.

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
