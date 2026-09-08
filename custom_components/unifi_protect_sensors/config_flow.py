"""Config flow for UniFi Protect Sensors."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
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

_VALIDATION_TIMEOUT = 10

# Credential fields; the rest of the entry (host, port, verify_ssl) is unchanged
# by a reauth, so only these are re-prompted.
_CREDENTIAL_KEYS = (CONF_USERNAME, CONF_PASSWORD, CONF_API_KEY)


async def async_validate_credentials(
    hass: HomeAssistant, config: Mapping[str, Any]
) -> str | None:
    """Check that the console accepts these settings.

    Returns a ``strings.json`` error key, or None when the credentials work.
    """
    host: str = config[CONF_HOST]
    port: int = config[CONF_PORT]
    api_key: str = config.get(CONF_API_KEY) or ""
    username: str = config.get(CONF_USERNAME) or ""
    password: str = config.get(CONF_PASSWORD) or ""
    verify_ssl: bool = config.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

    if not api_key and not (username and password):
        # Catch this here rather than letting the console reject a blank login,
        # which surfaces as a misleading "invalid username or password".
        return "missing_credentials"

    base_url = f"https://{host}:{port}"
    # ssl=False disables verification; ssl=None uses the default context (verifies)
    ssl = None if verify_ssl else False
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    timeout = aiohttp.ClientTimeout(total=_VALIDATION_TIMEOUT)

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
    except (aiohttp.ClientError, TimeoutError, OSError):
        # Network/TLS failures map to cannot_connect; programming errors are
        # allowed to surface instead of being masked.
        return "cannot_connect"
    return None


_CREDENTIAL_FIELDS = {
    vol.Optional(CONF_USERNAME, default=""): str,
    vol.Optional(CONF_PASSWORD, default=""): str,
    vol.Optional(CONF_API_KEY, default=""): str,
}

_CREDENTIALS_SCHEMA = vol.Schema(_CREDENTIAL_FIELDS)

_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        **_CREDENTIAL_FIELDS,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


class UniFiProtectSensorsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi Protect Sensors."""

    # v2: unique_id changed from host to host:port (see async_migrate_entry).
    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await async_validate_credentials(self.hass, user_input)
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
            step_id="user", data_schema=_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Start reauthentication after the console rejected our credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect fresh credentials for an existing entry and reload it."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            # Host, port and verify_ssl are not re-prompted, so validate the new
            # credentials against the connection settings already on the entry.
            candidate = {**entry.data, **entry.options, **user_input}
            error = await async_validate_credentials(self.hass, candidate)
            if error:
                errors["base"] = error
            else:
                # Update the entry and let the entry's update listener schedule
                # the reload. Calling async_update_reload_and_abort here would
                # reload a second time and is deprecated for entries that have a
                # listener (Home Assistant removes it in 2026.12).
                credentials = {key: user_input.get(key, "") for key in _CREDENTIAL_KEYS}
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, **credentials}
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_CREDENTIALS_SCHEMA,
            description_placeholders={"host": entry.data.get(CONF_HOST, "")},
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
                    ): bool
                }
            ),
        )
