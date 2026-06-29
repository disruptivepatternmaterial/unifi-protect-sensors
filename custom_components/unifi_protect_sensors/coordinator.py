"""DataUpdateCoordinator for UniFi Protect Sensors.

Data flows through two channels:

* **Bootstrap (REST)** — ``/proxy/protect/api/bootstrap`` gives a complete
  snapshot of every sensor. It is fetched every 30 seconds, guaranteeing that
  every sensor's ``last_updated`` timestamp stays fresh in Home Assistant even
  when a sensor is in a stable room and no WebSocket delta arrives.
* **WebSocket (push)** — ``/proxy/protect/ws/updates`` streams real-time deltas
  for each device. These deltas are merged into the snapshot between polls so
  that changing values appear immediately without waiting for the next REST poll.

Important: WebSocket updates must NOT call ``async_set_updated_data`` because
that method resets the coordinator's scheduled refresh timer, which would
prevent the 30-second bootstrap poll from ever running when the WS is active.
Instead, WS updates mutate ``self.data`` in place and call
``async_update_listeners()`` to push the change to entity callbacks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BOOTSTRAP_PATH, LOGIN_PATH, WS_PATH
from .helpers import deep_merge
from .protect_ws import decode_ws_message

_LOGGER = logging.getLogger(__name__)

# Bootstrap runs every 30 s so that stable-room sensors stay fresh in HA.
# WebSocket delivers changes immediately between polls.
_UPDATE_INTERVAL = timedelta(seconds=30)

# WebSocket reconnect backoff bounds (seconds)
_WS_BACKOFF_MIN = 2
_WS_BACKOFF_MAX = 60

# Timeout (seconds) for blocking REST calls and the WebSocket handshake. The HA
# shared session otherwise defaults to ~5 minutes, which lets a half-open
# connection stall the update loop.
_HTTP_TIMEOUT = 10


class ProtectSensorsCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll UniFi Protect sensor payloads and stream live updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="UniFi Protect Sensors",
            update_interval=_UPDATE_INTERVAL,
        )
        # Options override data so runtime changes (e.g. verify_ssl) take effect
        # after the entry is reloaded by the options update listener.
        config: dict[str, Any] = {**entry.data, **entry.options}
        self._entry_id: str = entry.entry_id
        self._host: str = config["host"]
        self._port: int = int(config.get("port", 443))
        self._username: str = config.get("username", "")
        self._password: str = config.get("password", "")
        self._api_key: str = config.get("api_key", "")
        self._verify_ssl: bool = bool(config.get("verify_ssl", False))
        self._base_url = f"https://{self._host}:{self._port}"
        self._session_cookie: str | None = None
        # ssl=False disables verification; ssl=None uses the default context (verifies)
        self._ssl: bool | None = None if self._verify_ssl else False
        self._last_update_id: str | None = None
        self._ws_task: asyncio.Task | None = None
        # Monotonic time the current WS connection was established, used to reset
        # reconnect backoff once a connection has proven stable.
        self._ws_connected_at: float | None = None
        # Serialises login so the bootstrap poll and WS reconnect can't both
        # spend a server session by logging in at the same time.
        self._login_lock = asyncio.Lock()

    async def _async_login(self) -> str:
        """Authenticate and return the TOKEN cookie value."""
        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)
        try:
            async with asyncio.timeout(_HTTP_TIMEOUT), session.post(
                f"{self._base_url}{LOGIN_PATH}",
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
            async with self._login_lock:
                # Re-check inside the lock: a concurrent caller may have logged
                # in while we were waiting.
                if self._session_cookie is None:
                    self._session_cookie = await self._async_login()
            headers["Cookie"] = f"TOKEN={self._session_cookie}"
        return headers

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch the full sensor snapshot from the Protect console bootstrap."""
        headers = await self._async_auth_headers()

        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)
        try:
            async with asyncio.timeout(_HTTP_TIMEOUT), session.get(
                f"{self._base_url}{BOOTSTRAP_PATH}",
                headers=headers,
                ssl=self._ssl,
            ) as resp:
                if resp.status in (401, 403):
                    # Token rejected. For cookie auth, clear it so the next poll
                    # re-authenticates (some consoles return 403, not 401, for a
                    # stale cookie). For a static API key there is nothing to
                    # refresh, so report it as a credential problem.
                    self._session_cookie = None
                    if self._api_key:
                        raise UpdateFailed(f"API key rejected (HTTP {resp.status})")
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
            self._ws_loop(), name=f"unifi_protect_sensors_ws_{self._entry_id}"
        )

    async def _ws_loop(self) -> None:
        """Maintain a WebSocket connection and merge live deltas into the snapshot."""
        backoff = _WS_BACKOFF_MIN
        while True:
            try:
                await self._ws_connect_and_listen()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the listener alive
                # _ws_connect_and_listen always raises (even on a clean close), so
                # reset backoff here when the connection had been stable for a
                # while — otherwise a few early blips would ratchet the delay to
                # the max permanently. A connection that survived >= the max
                # backoff is treated as healthy.
                if (
                    self._ws_connected_at is not None
                    and (self.hass.loop.time() - self._ws_connected_at) >= _WS_BACKOFF_MAX
                ):
                    backoff = _WS_BACKOFF_MIN
                self._ws_connected_at = None
                _LOGGER.debug("Protect WebSocket dropped (%s); reconnecting in %ds", err, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _WS_BACKOFF_MAX)

    async def _ws_connect_and_listen(self) -> None:
        """Open one WebSocket connection and process messages until it closes.

        Raises on both normal and abnormal closure so that ``_ws_loop`` always
        applies backoff before reconnecting — preventing a hot reconnect loop when
        the server accepts then immediately closes (e.g. stale lastUpdateId, expired
        token delivered via a close frame).
        """
        headers = await self._async_auth_headers()
        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)

        url = f"{self._base_url}{WS_PATH}"
        if self._last_update_id:
            url = f"{url}?lastUpdateId={self._last_update_id}"

        # Bound the handshake itself; `heartbeat` only guards an established
        # connection, not a console that accepts the socket then never upgrades.
        # `ws` is initialised to None and closed in a single finally so a socket
        # that gets established right as the timeout fires can't leak.
        ws = None
        try:
            async with asyncio.timeout(_HTTP_TIMEOUT):
                ws = await session.ws_connect(
                    url, headers=headers, ssl=self._ssl, heartbeat=30
                )
            self._ws_connected_at = self.hass.loop.time()
            _LOGGER.debug("Protect WebSocket connected")
            async for msg in ws:
                if msg.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    raise ConnectionError(f"WebSocket closed by server: {msg.data}")
                if msg.type != aiohttp.WSMsgType.BINARY:
                    continue
                self._handle_ws_message(msg.data)
            # Loop ended without a close frame — treat as server-initiated close.
            raise ConnectionError("WebSocket connection ended unexpectedly")
        except aiohttp.WSServerHandshakeError as err:
            # Auth failure during WS upgrade — invalidate cookie so the next attempt
            # triggers a fresh login instead of retrying a dead token.
            if err.status in (401, 403):
                _LOGGER.debug("Protect WebSocket auth failed (%d); clearing session cookie", err.status)
                self._session_cookie = None
            raise
        finally:
            if ws is not None:
                await ws.close()

    def _handle_ws_message(self, raw: bytes) -> None:
        """Decode one WS message and merge it into the current snapshot."""
        try:
            message = decode_ws_message(raw)
        except Exception as err:  # noqa: BLE001 - never let one bad frame kill the stream
            _LOGGER.debug("Failed to decode Protect WS message: %s", err)
            return

        action = message.action

        # Advance the cursor for ALL models before filtering — non-sensor frames
        # also carry newUpdateId and skipping them causes a stale cursor on reconnect.
        if action.get("newUpdateId"):
            self._last_update_id = action["newUpdateId"]

        if action.get("modelKey") != "sensor":
            return

        device_id = action.get("id")
        if not device_id:
            return

        verb = action.get("action")

        # Use the live dict even when empty ({} is falsy, so `or {}` would make a
        # throwaway copy and silently drop a remove/merge).
        data = self.data if self.data is not None else {}

        if verb == "remove":
            if device_id in data:
                data.pop(device_id, None)
                self.async_update_listeners()
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

        # Mutate data in place and notify listeners WITHOUT resetting the
        # coordinator's scheduled refresh timer (unlike async_set_updated_data).
        deep_merge(existing, message.data)
        self.async_update_listeners()

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
