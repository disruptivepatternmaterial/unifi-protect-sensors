"""DataUpdateCoordinator for UniFi Protect Sensors.

Data flows through two channels:

* **Bootstrap (REST)** — ``/proxy/protect/api/bootstrap`` gives a complete
  snapshot of every sensor. It is fetched on startup and re-fetched on a slow
  interval to self-heal any missed updates.
* **WebSocket (push)** — ``/proxy/protect/ws/updates`` streams real-time deltas
  for each device. These deltas are merged into the snapshot so battery-powered
  environmental sensors update the instant they report, instead of waiting for
  the next REST poll.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .helpers import deep_merge
from .protect_ws import decode_ws_message

_LOGGER = logging.getLogger(__name__)

# Bootstrap is now a slow self-healing resync; the WebSocket carries live data.
_UPDATE_INTERVAL = timedelta(minutes=5)
_BOOTSTRAP_PATH = "/proxy/protect/api/bootstrap"
_LOGIN_PATH = "/api/auth/login"
_WS_PATH = "/proxy/protect/ws/updates"

# WebSocket reconnect backoff bounds (seconds)
_WS_BACKOFF_MIN = 2
_WS_BACKOFF_MAX = 60


class ProtectSensorsCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll UniFi Protect sensor payloads and stream live updates."""

    def __init__(self, hass: HomeAssistant, entry_data: dict[str, Any]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="UniFi Protect Sensors",
            update_interval=_UPDATE_INTERVAL,
        )
        self._host: str = entry_data["host"]
        self._port: int = int(entry_data.get("port", 443))
        self._username: str = entry_data.get("username", "")
        self._password: str = entry_data.get("password", "")
        self._api_key: str = entry_data.get("api_key", "")
        self._verify_ssl: bool = bool(entry_data.get("verify_ssl", False))
        self._base_url = f"https://{self._host}:{self._port}"
        self._session_cookie: str | None = None
        # ssl=False disables verification; ssl=None uses the default context (verifies)
        self._ssl: bool | None = None if self._verify_ssl else False
        self._last_update_id: str | None = None
        self._ws_task: asyncio.Task | None = None

    async def _async_login(self) -> str:
        """Authenticate and return the TOKEN cookie value."""
        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)
        try:
            async with session.post(
                f"{self._base_url}{_LOGIN_PATH}",
                json={"username": self._username, "password": self._password},
                ssl=self._ssl,
            ) as resp:
                if resp.status not in (200, 201):
                    raise UpdateFailed(f"Login failed with HTTP {resp.status}")
                token = resp.cookies.get("TOKEN") or resp.cookies.get("token")
                if token is None:
                    raise UpdateFailed("Login succeeded but no TOKEN cookie returned")
                return token.value
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Login request failed: {err}") from err

    async def _async_auth_headers(self) -> dict[str, str]:
        """Build auth headers, logging in for cookie auth when needed."""
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        else:
            if self._session_cookie is None:
                self._session_cookie = await self._async_login()
            headers["Cookie"] = f"TOKEN={self._session_cookie}"
        return headers

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch the full sensor snapshot from the Protect console bootstrap."""
        headers = await self._async_auth_headers()

        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)
        try:
            async with session.get(
                f"{self._base_url}{_BOOTSTRAP_PATH}",
                headers=headers,
                ssl=self._ssl,
            ) as resp:
                if resp.status == 401:
                    # Session expired; clear token so next poll re-authenticates
                    self._session_cookie = None
                    raise UpdateFailed("Session expired; will re-authenticate on next update")
                if resp.status != 200:
                    raise UpdateFailed(f"Bootstrap endpoint returned HTTP {resp.status}")
                payload: Any = await resp.json()
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Cannot reach Protect console: {err}") from err

        if not isinstance(payload, dict):
            raise UpdateFailed(f"Unexpected bootstrap payload type: {type(payload).__name__}")
        self._last_update_id = payload.get("lastUpdateId")
        sensors_list = payload.get("sensors", [])
        if not isinstance(sensors_list, list):
            raise UpdateFailed("Bootstrap payload missing 'sensors' list")
        result = {d["id"]: d for d in sensors_list if isinstance(d, dict) and "id" in d}

        _LOGGER.debug(
            "Protect bootstrap: %d device(s) — %s",
            len(result),
            ", ".join(
                f"{d.get('name', did)}({d.get('type') or d.get('modelKey', '?')})"
                for did, d in result.items()
            ),
        )

        # Start the live WebSocket listener once we have an initial snapshot.
        self._ensure_ws_task()
        return result

    # ------------------------------------------------------------------
    # WebSocket live updates
    # ------------------------------------------------------------------

    def _ensure_ws_task(self) -> None:
        """Start the background WebSocket listener if it isn't already running."""
        if self._ws_task is not None and not self._ws_task.done():
            return
        self._ws_task = self.hass.async_create_background_task(
            self._ws_loop(), name="unifi_protect_sensors_ws"
        )

    async def _ws_loop(self) -> None:
        """Maintain a WebSocket connection and merge live deltas into the snapshot."""
        backoff = _WS_BACKOFF_MIN
        while True:
            try:
                await self._ws_connect_and_listen()
                backoff = _WS_BACKOFF_MIN
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the listener alive
                _LOGGER.debug("Protect WebSocket dropped (%s); reconnecting in %ds", err, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _WS_BACKOFF_MAX)

    async def _ws_connect_and_listen(self) -> None:
        """Open one WebSocket connection and process messages until it closes."""
        headers = await self._async_auth_headers()
        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)

        url = f"{self._base_url}{_WS_PATH}"
        if self._last_update_id:
            url = f"{url}?lastUpdateId={self._last_update_id}"

        async with session.ws_connect(url, headers=headers, ssl=self._ssl, heartbeat=30) as ws:
            _LOGGER.debug("Protect WebSocket connected")
            async for msg in ws:
                if msg.type.name in ("CLOSE", "CLOSING", "CLOSED", "ERROR"):
                    break
                if msg.type.name != "BINARY":
                    continue
                self._handle_ws_message(msg.data)

    def _handle_ws_message(self, raw: bytes) -> None:
        """Decode one WS message and merge it into the current snapshot."""
        try:
            message = decode_ws_message(raw)
        except Exception as err:  # noqa: BLE001 - never let one bad frame kill the stream
            _LOGGER.debug("Failed to decode Protect WS message: %s", err)
            return

        action = message.action
        if action.get("modelKey") != "sensor":
            return

        device_id = action.get("id")
        if not device_id:
            return

        verb = action.get("action")
        if action.get("newUpdateId"):
            self._last_update_id = action["newUpdateId"]

        data = self.data or {}

        if verb == "remove":
            if device_id in data:
                new_data = dict(data)
                new_data.pop(device_id, None)
                self.async_set_updated_data(new_data)
            return

        if verb == "add":
            # A newly adopted sensor; pull a fresh snapshot to pick it up fully.
            self.hass.async_create_task(self.async_request_refresh())
            return

        if verb != "update":
            return

        existing = data.get(device_id)
        if existing is None:
            # Delta for a sensor we don't know yet — resync to fetch it whole.
            self.hass.async_create_task(self.async_request_refresh())
            return

        merged = deep_merge(dict(existing), message.data)
        new_data = dict(data)
        new_data[device_id] = merged
        self.async_set_updated_data(new_data)

    async def async_shutdown(self) -> None:
        """Cancel the WebSocket listener and run base shutdown."""
        if self._ws_task is not None:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._ws_task = None
        await super().async_shutdown()
