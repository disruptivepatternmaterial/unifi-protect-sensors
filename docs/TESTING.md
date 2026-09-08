# Testing Guide

## Running Tests

The unit tests stub Home Assistant (see `tests/conftest.py`), so no HA install
is required. `aiohttp` and `voluptuous` are needed for real: the config flow
catches genuine `aiohttp` exception classes and builds real voluptuous schemas,
so stubbing them would make those code paths untestable.

```bash
python3 -m venv .venv_test
.venv_test/bin/pip install pytest pytest-asyncio ruff aiohttp voluptuous
.venv_test/bin/pytest tests/ -v
```

The same commands run in CI (`.github/workflows/ci.yml`) on every push and pull
request, together with Home Assistant `hassfest` and HACS validation.

## Linting

The repo is linted with [ruff](https://docs.astral.sh/ruff/) using the config in
`pyproject.toml` (rule sets `E,F,W,I,UP`):

```bash
ruff check custom_components/ tests/
ruff check custom_components/ tests/ --fix   # auto-fix import sorting, etc.
```

## Test Coverage

### Unit tests (no HA runtime required)

- `tests/test_sensor_descriptions.py` — entity descriptions (unique keys,
  payload_field, units, PM device classes), `description.supports()` device-model
  matching, entity property logic (native_value, is_on, availability incl.
  DISCONNECTED), and leak/tamper/battery null-state semantics. `nox_index` is
  asserted absent (the UP-AirQuality API does not expose it).
- `tests/test_entity.py` — `DeviceInfo` construction incl. the null-name and
  null-type fallbacks, availability rules, preservation of a genuine `0`
  reading, and `strings.json` ↔ `translations/en.json` parity.
- `tests/test_config_flow.py` — credential validation (missing credentials,
  rejected key/password, endpoint selection, network-error mapping) and the
  reauth flow (form redisplay on failure, credential replacement on success).
- `tests/test_protect_ws.py` — WebSocket frame decoder (headers, deflate,
  zlib size cap, truncated/incomplete streams) and `deep_merge`.
- `tests/test_dynamic_discovery.py` — entities created at setup, idempotent
  re-discovery, and late-adopted devices.
- `tests/test_coordinator.py` — login-lock concurrency, options-over-data,
  API-key vs cookie auth header selection, session invalidation semantics, and
  the auth-failure paths that trigger reauth.
- `tests/test_init_migration.py` — config-entry migration (v1 host -> v2
  host:port), default-port and missing-host fallbacks.

### Live validation (manual, requires hardware)

1. Install via HACS and confirm entities appear in HA
2. Verify values update via Protect websocket pushes
3. Confirm history graphs render correctly
4. Trigger water leak and tamper events; verify binary sensor state

## Adding Fixtures

See PAYLOAD_GUIDE.md for how to capture and sanitize real device payloads.
