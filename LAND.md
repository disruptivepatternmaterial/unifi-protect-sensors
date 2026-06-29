# Landing Plan — Multi-Model Review Fixes

Source: adversarial multi-model code review (GPT-5.3 Codex, Claude Opus 4.8, Claude Sonnet 4.6 max, Claude Sonnet 4.6 medium, Gemini 3.5 Flash, GPT-5.5) of the `unifi_protect_sensors` integration on `main` (v0.5.4).

Cleared by all six reviewers (no changes needed): binary-frame decoder bounds + zlib-bomb cap (`protect_ws.py`), `deep_merge` in-place mutation, WS task cancellation in `async_shutdown`.

---

## Act on (clear correctness/robustness wins) — DONE

All six landed across commits `58dc9f3`, `4e36d09`, `2c598ce`.

- [x] **#1 Dead options flow (`verify_ssl`)** — 6/6, Critical — `58dc9f3`
  - Coordinator now built from `{**entry.data, **entry.options}` ([coordinator.py](custom_components/unifi_protect_sensors/coordinator.py)) and `_async_update_listener` reloads the entry on options change ([__init__.py](custom_components/unifi_protect_sensors/__init__.py)).

- [x] **#2 No dynamic entity creation** — 6/6, High — `2c598ce`
  - Both platforms run `_discover_entities()` once and register it via `coordinator.async_add_listener`, diffing known device IDs / unique IDs so post-setup devices get entities.

- [x] **#3 Bidirectional substring device-type match** — 6/6, Warning — `2c598ce`
  - Replaced with exact case-insensitive `device_type_matches` helper ([helpers.py](custom_components/unifi_protect_sensors/helpers.py)); blank/unknown type matches nothing. Regression tests added.

- [x] **#6 Config flow validates wrong endpoint** — 4/6, Warning — `4e36d09`
  - API-key validation now hits `/proxy/protect/api/bootstrap` (shared `BOOTSTRAP_PATH`), treats 403 like 401.

- [x] **#8 WS task leak on partial setup failure** — 3/6, Warning — `58dc9f3`
  - `config_entry=entry` passed to the coordinator; `async_setup_entry` tears the coordinator down if `async_forward_entry_setups` raises.

- [x] **#10 403 doesn't clear cookie** — 2/6, Warning — `58dc9f3`
  - `if resp.status in (401, 403):` clears the session cookie and re-auths.

---

## Consider

- [ ] **#4 WS backoff reset is dead code** — 3/6 (Opus dissents). `_ws_connect_and_listen` always raises, so `backoff = _WS_BACKOFF_MIN` (`coordinator.py:166`) is unreachable; delay ratchets to 60s. Fix: track connection uptime and reset backoff after a connection survives longer than a threshold.
- [ ] **#5 Leak/tamper `null` -> Unknown not Off** — 4/6 (Sonnet-max dissents). `is_on` returns `None` for null timestamps (`binary_sensor.py:129-130`); breaks `to: 'off'` automations. Fix: per-description `null_means_off` flag, set on leak + tamper; keep tri-state for `batteryStatus.isLow`.
- [ ] **#7 Host-only unique_id** — 3/6. `async_set_unique_id(host)` (`config_flow.py:89`) blocks two consoles on same host, breaks on IP change. Fix: use `host:port`, or MAC from bootstrap.
- [x] **#11 No timeouts on runtime HTTP/WS** — 2/6 — `6fc2180`. Login, bootstrap, and the WS handshake wrapped in `asyncio.timeout(10)`.
- [x] **PM1/PM4 missing `device_class`** — lone (GPT-5.5) — `7bbc1dc`. Verified `SensorDeviceClass.PM1`/`PM4` exist in HA ([sensor entity docs](https://developers.home-assistant.io/docs/core/entity/sensor/)); assigned + stub + test updated.
- [x] **Availability semantics** — lone — done (device-state option). Entities now go unavailable on explicit `state == "DISCONNECTED"` (Gemini's stale-offline concern), treating unknown/transient states as available. The REST-vs-WS decoupling half (Opus) was intentionally NOT changed: WS resyncs every 30s and decoupling risks masking real outages. Tests added.

### Consider — also done

- [x] **#4 WS backoff reset dead code** — 3/6 — `6fc2180`. Backoff resets after a connection stays up >= max backoff.
- [x] **#5 Leak/tamper null -> Unknown** — 4/6 — `5a632d5`. `null_means_off` flag maps null -> off for leak/tamper.
- [x] **#7 Host-only unique_id** — 3/6 — `d6860f3`. Now `host:port`.

---

## Noted (nits) — DONE

- [x] **#9 Concurrent double-login** — 2/6 — `96ff1d1`. `asyncio.Lock` around the login block.
- [x] **#12 Broad `except Exception` in flow** — 2/6 — `977a3d1`. Narrowed to `(aiohttp.ClientError, TimeoutError, OSError)`.
- [x] **#13 zlib stream-completeness** — 2/6 — `537f7c4`. Assert `dec.eof`; wrap `zlib.error` as `ValueError`. (Did not add the strict trailing-bytes-after-frames assertion — no evidence Protect emits exactly two frames with no padding, so that would be fragile.)
- [x] **`_attr_device_info` plain dict** — lone — `0c7a147`. Now `DeviceInfo`.
- [x] **`self.data or {}` breaks remove on empty dict** — lone — `96ff1d1`.
- [x] Minor: duplicated `_LOGIN_PATH` (shared const), redundant `dev_reg` calls (guarded by `known_devices`), per-entry WS task name, `Platform` enum (`0c7a147`).
- [ ] **`codeowners: []`** — left blank (maintainer GH handle not assumed here).
- [ ] **`async_get_clientsession(verify_ssl=...)` vs per-request `ssl=`** — lone. Left as-is: both point the same way; the per-request `ssl` is belt-and-suspenders and removing the param risks subtle session/cookie-jar selection changes. Revisit only if it causes confusion.

---

## Verify before acting

- [ ] **Shared client-session cookie collision (Gemini)** — EVALUATED, deferred. aiohttp's shared cookie jar is keyed per-domain, so cross-console clobber needs the same host; and we already send the TOKEN via an explicit header. Real risk is narrow (leak to another integration talking to the same host). Switching cookie auth to a dedicated `async_create_clientsession` is the proper hardening but is a session-lifecycle change deserving its own focused effort + tests; API-key auth (recommended) is unaffected. Deferred, not blocking.

---

## Suggested landing order

1. #1 dead options flow + #8 `config_entry=` (small, high value)
2. #2 dynamic entity creation (largest change)
3. #3 device-type matching + #6 validation endpoint
4. #10 403 handling + #11 timeouts + #5 leak/tamper Off
5. #4 backoff reset + #7 unique_id + PM1/PM4
6. Nits batch
