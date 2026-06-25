"""DataUpdateCoordinator for UniFi Protect Sensors."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

_UPDATE_INTERVAL = timedelta(seconds=30)
_SENSORS_PATH = "/proxy/protect/integration/v1/sensors"
_LOGIN_PATH = "/api/auth/login"


class ProtectSensorsCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll UniFi Protect sensor payloads."""

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

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch sensor data from the Protect console."""
        headers: dict[str, str] = {}

        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        else:
            if self._session_cookie is None:
                self._session_cookie = await self._async_login()
            headers["Cookie"] = f"TOKEN={self._session_cookie}"

        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)
        try:
            async with session.get(
                f"{self._base_url}{_SENSORS_PATH}",
                headers=headers,
                ssl=self._ssl,
            ) as resp:
                if resp.status == 401:
                    # Session expired; clear token so next poll re-authenticates
                    self._session_cookie = None
                    raise UpdateFailed("Session expired; will re-authenticate on next update")
                if resp.status != 200:
                    raise UpdateFailed(f"Sensors endpoint returned HTTP {resp.status}")
                payload: Any = await resp.json()
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Cannot reach Protect console: {err}") from err

        if isinstance(payload, list):
            return {d["id"]: d for d in payload if isinstance(d, dict) and "id" in d}
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            return {d["id"]: d for d in payload["data"] if isinstance(d, dict) and "id" in d}
        raise UpdateFailed(f"Unexpected sensors payload shape: {type(payload).__name__}")
