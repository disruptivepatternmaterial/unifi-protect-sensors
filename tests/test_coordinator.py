"""Tests for coordinator behavior that needs no live network."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parents[1]))


def _make_coordinator(data=None, options=None):
    from custom_components.unifi_protect_sensors.coordinator import ProtectSensorsCoordinator

    entry = MagicMock()
    entry.data = data or {"host": "console", "username": "u", "password": "p"}
    entry.options = options or {}
    entry.entry_id = "entry1"
    hass = MagicMock()
    return ProtectSensorsCoordinator(hass, entry)


class TestLoginLock:
    async def test_concurrent_auth_logs_in_once(self):
        coord = _make_coordinator()
        coord._session_cookie = None

        calls = 0

        async def fake_login():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)  # yield so both coroutines overlap
            return "tok"

        coord._async_login = fake_login

        results = await asyncio.gather(
            coord._async_auth_headers(), coord._async_auth_headers()
        )

        assert calls == 1, "login should run once under the lock, not per-caller"
        assert all(r["Cookie"] == "TOKEN=tok" for r in results)


class TestOptionsOverrideData:
    def test_options_override_data(self):
        coord = _make_coordinator(
            data={"host": "console", "verify_ssl": False},
            options={"verify_ssl": True},
        )
        assert coord._verify_ssl is True
        # ssl=None means "use the verifying default context"
        assert coord._ssl is None

    async def test_api_key_auth_uses_bearer_and_skips_login(self):
        coord = _make_coordinator(data={"host": "console", "api_key": "abc"})

        async def fail_login():
            raise AssertionError("login must not be called when an API key is set")

        coord._async_login = fail_login

        headers = await coord._async_auth_headers()

        assert headers["Authorization"] == "Bearer abc"
        assert "Cookie" not in headers
