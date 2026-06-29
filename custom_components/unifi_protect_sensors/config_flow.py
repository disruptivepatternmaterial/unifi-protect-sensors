"""Config flow for UniFi Protect Sensors."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    BOOTSTRAP_PATH,
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    LOGIN_PATH,
)

_LOGGER = logging.getLogger(__name__)


async def _async_validate_credentials(hass, host: str, port: int, username: str, password: str, api_key: str, verify_ssl: bool) -> str | None:
    """Try to reach the console and authenticate. Returns error key or None on success."""
    base_url = f"https://{host}:{port}"
    # ssl=False disables verification; ssl=None uses the default context (verifies)
    ssl = None if verify_ssl else False
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        if api_key:
            # Validate against the same bootstrap endpoint the coordinator polls,
            # so a key that authenticates but lacks bootstrap access is rejected
            # here instead of failing silently after setup.
            async with session.get(
                f"{base_url}{BOOTSTRAP_PATH}",
                headers={"Authorization": f"Bearer {api_key}"},
                ssl=ssl,
                timeout=timeout,
            ) as resp:
                if resp.status in (401, 403):
                    return "invalid_api_key"
                if resp.status != 200:
                    return "cannot_connect"
        else:
            async with session.post(
                f"{base_url}{LOGIN_PATH}",
                json={"username": username, "password": password},
                ssl=ssl,
                timeout=timeout,
            ) as resp:
                if resp.status in (401, 403):
                    return "invalid_auth"
                if resp.status not in (200, 201):
                    return "cannot_connect"
    except Exception:
        return "cannot_connect"
    return None


class UniFiProtectSensorsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi Protect Sensors."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await _async_validate_credentials(
                self.hass,
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                username=user_input.get(CONF_USERNAME, ""),
                password=user_input.get(CONF_PASSWORD, ""),
                api_key=user_input.get(CONF_API_KEY, ""),
                verify_ssl=user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            )
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"UniFi Protect Sensors ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_USERNAME, default=""): str,
                    vol.Optional(CONF_PASSWORD, default=""): str,
                    vol.Optional(CONF_API_KEY, default=""): str,
                    vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return UniFiProtectSensorsOptionsFlow()


class UniFiProtectSensorsOptionsFlow(config_entries.OptionsFlow):
    """Handle options for UniFi Protect Sensors."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_VERIFY_SSL,
                        default=self.config_entry.options.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                    ): bool,
                }
            ),
        )
