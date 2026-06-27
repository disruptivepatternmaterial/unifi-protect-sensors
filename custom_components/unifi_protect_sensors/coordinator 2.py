"""DataUpdateCoordinator for UniFi Protect Sensors."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
SENSORS_PATH = "/proxy/protect/integration/v1/sensors"
LOGIN_PATH = "/api/auth/login"


class ProtectSensorsCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    """Polls the Protect console /v1/sensors endpoint every 30 seconds."""

    def __init__(self, hass: HomeAssistant, entry_data: dict[str, Any]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="UniFi Protect Sensors",
            update_interval=UPDATE_INTERVAL,
        )
        self._host: str = entry_data["host"]
        self._port: int = entry_data.get("port", 443)
        self._username: str = entry_data.get("username", "")
        self._password: str = entry_data.get("password", "")
        self._api_key: str = entry_data.get("api_key", "")
        self._verify_ssl: bool = entry_data.get("verify_ssl", False)
        self._base_url = f"https://{self._host}:{self._port}"
        self._session_cookie: str | None = None

    async def _async_login(self) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}{LOGIN_PATH}",
                json={"username": self._username, "password": self._password},
                ssl=self._verify_ssl,
            ) as resp:
                if resp.status not in (200, 201):
                    raise UpdateFailed(f"Login failed with HTTP {resp.status}")
                cookie = resp.cookies.get("TOKEN") or resp.cookies.get("token")
                if cookie is None:
                    raise UpdateFailed("Login succeeded but no TOKEN cookie in response")
                return cookie.value

    async def _async_update_data(self) -> dict[str, dict]:
        headers: dict[str, str] = {}

        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        else:
            if self._session_cookie is None:
                self._session_cookie = await self._async_login()
            headers["Cookie"] = f"TOKEN={self._session_cookie}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._base_url}{SENSORS_PATH}",
                    headers=headers,
                    ssl=self._verify_ssl,
                ) as resp:
                    if resp.status == 401:
                        self._session_cookie = None
                        raise UpdateFailed("Auth expired; will re-login on next poll")
                    if resp.status != 200:
                        raise UpdateFailed(
                            f"Sensors endpoint returned HTTP {resp.status}"
                        )
                    payload = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot reach Protect console: {err}") from err

        if isinstance(payload, list):
            return {d["id"]: d for d in payload if "id" in d}
        if isinstance(payload, dict) and "data" in payload:
            return {d["id"]: d for d in payload["data"] if "id" in d}
        raise UpdateFailed(f"Unexpected sensors payload shape: {type(payload)!r}")
