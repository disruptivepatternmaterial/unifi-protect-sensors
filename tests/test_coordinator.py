"""Tests for coordinator behavior that needs no live network."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))


class _FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status
        self.cookies: dict = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info) -> bool:
        return False

    async def json(self):
        return {"sensors": []}


class _FakeSession:
    """Stands in for the shared aiohttp session with canned status codes."""

    def __init__(self, get_status: int = 200, post_status: int = 200) -> None:
        self._get_status = get_status
        self._post_status = post_status

    def get(self, url, **kwargs):
        return _FakeResponse(self._get_status)

    def post(self, url, **kwargs):
        return _FakeResponse(self._post_status)


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


class TestSessionInvalidation:
    """A rejected cookie must be dropped without discarding a newer session."""

    async def test_rejected_cookie_is_cleared(self):
        coord = _make_coordinator()
        coord._session_cookie = "stale"

        await coord._async_invalidate_session("stale")

        assert coord._session_cookie is None

    async def test_newer_cookie_survives_a_late_rejection(self):
        """A login that landed after the failed request must not be thrown away,
        or the two would invalidate each other in a reconnect loop."""
        coord = _make_coordinator()
        coord._session_cookie = "fresh"

        await coord._async_invalidate_session("stale")

        assert coord._session_cookie == "fresh"

    async def test_api_key_auth_has_no_session_to_drop(self):
        coord = _make_coordinator(data={"host": "console", "api_key": "abc"})
        coord._session_cookie = "irrelevant"

        await coord._async_invalidate_session(None)

        assert coord._session_cookie == "irrelevant"


class TestAuthFailuresRequestReauth:
    """Bad credentials must surface as ConfigEntryAuthFailed so Home Assistant
    prompts for new ones instead of retrying a dead password every 30 seconds."""

    async def test_login_rejection_raises_auth_failed(self):
        from homeassistant.exceptions import ConfigEntryAuthFailed

        coord = _make_coordinator()
        coord._session_cookie = None

        with patch(
            "custom_components.unifi_protect_sensors.coordinator.async_get_clientsession",
            return_value=_FakeSession(post_status=401),
        ), pytest.raises(ConfigEntryAuthFailed):
            await coord._async_login()

    async def test_login_server_error_is_a_transient_update_failure(self):
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coord = _make_coordinator()

        with patch(
            "custom_components.unifi_protect_sensors.coordinator.async_get_clientsession",
            return_value=_FakeSession(post_status=500),
        ), pytest.raises(UpdateFailed):
            await coord._async_login()

    async def test_rejected_api_key_raises_auth_failed(self):
        from homeassistant.exceptions import ConfigEntryAuthFailed

        coord = _make_coordinator(data={"host": "console", "api_key": "abc"})

        with patch(
            "custom_components.unifi_protect_sensors.coordinator.async_get_clientsession",
            return_value=_FakeSession(get_status=403),
        ), pytest.raises(ConfigEntryAuthFailed):
            await coord._async_update_data()

    async def test_expired_cookie_is_a_retryable_update_failure(self):
        """Cookie auth can recover on its own, so it must not demand reauth."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coord = _make_coordinator()
        coord._session_cookie = "stale"

        with patch(
            "custom_components.unifi_protect_sensors.coordinator.async_get_clientsession",
            return_value=_FakeSession(get_status=401),
        ), pytest.raises(UpdateFailed):
            await coord._async_update_data()

        assert coord._session_cookie is None, "the rejected cookie must be dropped"
