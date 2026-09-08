"""Tests for credential validation and the reauth flow.

The config flow is what decides whether the integration can be set up at all, so
it is exercised here against a fake aiohttp session rather than a live console.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

CONFIG_FLOW = "custom_components.unifi_protect_sensors.config_flow"


def _module():
    return importlib.import_module(CONFIG_FLOW)


class _FakeResponse:
    """Async context manager standing in for an aiohttp response."""

    def __init__(self, status: int) -> None:
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info) -> bool:
        return False


class _FakeSession:
    """Records the request made and returns a canned status (or raises)."""

    def __init__(self, status: int = 200, raises: Exception | None = None) -> None:
        self._status = status
        self._raises = raises
        self.calls: list[tuple[str, str]] = []

    def _respond(self, method: str, url: str):
        self.calls.append((method, url))
        if self._raises is not None:
            raise self._raises
        return _FakeResponse(self._status)

    def get(self, url, **kwargs):
        return self._respond("GET", url)

    def post(self, url, **kwargs):
        return self._respond("POST", url)


def _patch_session(session: _FakeSession):
    return patch(f"{CONFIG_FLOW}.async_get_clientsession", return_value=session)


def _config(**overrides):
    base = {"host": "console.local", "port": 443, "verify_ssl": False}
    return {**base, **overrides}


class TestValidateCredentials:
    async def test_module_imports(self):
        """A broken config_flow means the integration cannot be added at all."""
        assert _module().UniFiProtectSensorsConfigFlow.VERSION == 2

    async def test_blank_credentials_rejected_without_a_request(self):
        session = _FakeSession()
        with _patch_session(session):
            error = await _module().async_validate_credentials(MagicMock(), _config())
        assert error == "missing_credentials"
        assert session.calls == [], "no request should be made without credentials"

    async def test_username_without_password_rejected(self):
        session = _FakeSession()
        with _patch_session(session):
            error = await _module().async_validate_credentials(
                MagicMock(), _config(username="u", password="")
            )
        assert error == "missing_credentials"
        assert session.calls == []

    async def test_api_key_validates_against_bootstrap(self):
        session = _FakeSession(status=200)
        with _patch_session(session):
            error = await _module().async_validate_credentials(
                MagicMock(), _config(api_key="key")
            )
        assert error is None
        method, url = session.calls[0]
        assert method == "GET"
        assert url.endswith("/proxy/protect/api/bootstrap")

    @pytest.mark.parametrize("status", [401, 403])
    async def test_rejected_api_key(self, status):
        with _patch_session(_FakeSession(status=status)):
            error = await _module().async_validate_credentials(
                MagicMock(), _config(api_key="key")
            )
        assert error == "invalid_api_key"

    async def test_api_key_without_bootstrap_access_is_cannot_connect(self):
        with _patch_session(_FakeSession(status=404)):
            error = await _module().async_validate_credentials(
                MagicMock(), _config(api_key="key")
            )
        assert error == "cannot_connect"

    @pytest.mark.parametrize("status", [401, 403])
    async def test_rejected_password(self, status):
        with _patch_session(_FakeSession(status=status)):
            error = await _module().async_validate_credentials(
                MagicMock(), _config(username="u", password="p")
            )
        assert error == "invalid_auth"

    async def test_password_login_posts_to_login_path(self):
        session = _FakeSession(status=200)
        with _patch_session(session):
            error = await _module().async_validate_credentials(
                MagicMock(), _config(username="u", password="p")
            )
        assert error is None
        method, url = session.calls[0]
        assert method == "POST"
        assert url.endswith("/api/auth/login")

    async def test_api_key_takes_precedence_over_password(self):
        session = _FakeSession(status=200)
        with _patch_session(session):
            await _module().async_validate_credentials(
                MagicMock(), _config(api_key="key", username="u", password="p")
            )
        assert session.calls[0][0] == "GET", "api key path must win over cookie login"

    @pytest.mark.parametrize(
        "error", [aiohttp.ClientError(), TimeoutError(), OSError("unreachable")]
    )
    async def test_network_failures_map_to_cannot_connect(self, error):
        with _patch_session(_FakeSession(raises=error)):
            result = await _module().async_validate_credentials(
                MagicMock(), _config(api_key="key")
            )
        assert result == "cannot_connect"


class _FakeConfigEntries:
    """Records entry updates the way Home Assistant applies them.

    Home Assistant fires the entry's update listener (which reloads the entry)
    whenever the data actually changes, so the flow must not schedule a reload of
    its own on top of that.
    """

    def __init__(self) -> None:
        self.reloads_scheduled = 0

    def async_update_entry(self, entry, *, data=None, **kwargs) -> bool:
        if data is None or data == entry.data:
            return False
        entry.data = data
        self.reloads_scheduled += 1  # the update listener reloads on change
        return True

    def async_schedule_reload(self, entry_id) -> None:
        self.reloads_scheduled += 1


class TestReauthFlow:
    def _flow(self, entry):
        module = _module()
        flow = module.UniFiProtectSensorsConfigFlow()
        flow.hass = MagicMock()
        flow.hass.config_entries = _FakeConfigEntries()
        flow._get_reauth_entry = lambda: entry
        return flow

    def _entry(self):
        return SimpleNamespace(
            data={"host": "console.local", "port": 443, "username": "old", "password": "stale"},
            options={},
        )

    async def test_form_is_shown_first(self):
        result = await self._flow(self._entry()).async_step_reauth({})
        assert result["type"] == "form"
        assert result["step_id"] == "reauth_confirm"

    async def test_bad_credentials_redisplay_the_form(self):
        flow = self._flow(self._entry())
        with _patch_session(_FakeSession(status=401)):
            result = await flow.async_step_reauth_confirm({"username": "u", "password": "wrong"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_auth"}

    async def test_accepted_credentials_replace_the_stored_ones(self):
        entry = self._entry()
        flow = self._flow(entry)
        with _patch_session(_FakeSession(status=200)):
            result = await flow.async_step_reauth_confirm({"api_key": "fresh-key"})

        assert result["type"] == "abort"
        assert result["reason"] == "reauth_successful"
        assert entry.data["api_key"] == "fresh-key"
        # Switching to an API key must clear the stale username/password, not
        # leave them behind for the coordinator to prefer.
        assert entry.data["username"] == ""
        assert entry.data["password"] == ""
        # Connection settings are not re-prompted and must survive untouched.
        assert entry.data["host"] == "console.local"
        assert entry.data["port"] == 443

    async def test_entry_is_reloaded_exactly_once(self):
        """The entry's update listener already reloads on change; scheduling a
        second reload tears the integration down and back up twice."""
        entry = self._entry()
        flow = self._flow(entry)
        with _patch_session(_FakeSession(status=200)):
            await flow.async_step_reauth_confirm({"api_key": "fresh-key"})

        assert flow.hass.config_entries.reloads_scheduled == 1

    async def test_failed_reauth_leaves_the_entry_untouched(self):
        entry = self._entry()
        original = dict(entry.data)
        flow = self._flow(entry)
        with _patch_session(_FakeSession(status=401)):
            await flow.async_step_reauth_confirm({"username": "u", "password": "wrong"})

        assert entry.data == original
        assert flow.hass.config_entries.reloads_scheduled == 0

    async def test_reauth_validates_against_the_stored_host(self):
        """Host/port are not re-prompted, so they must come from the entry."""
        session = _FakeSession(status=200)
        flow = self._flow(self._entry())
        with _patch_session(session):
            await flow.async_step_reauth_confirm({"api_key": "fresh-key"})
        assert session.calls[0][1].startswith("https://console.local:443")
