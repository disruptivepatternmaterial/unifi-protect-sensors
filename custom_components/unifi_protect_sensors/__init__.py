"""UniFi Protect environmental and air-quality sensors."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DEFAULT_PORT, DOMAIN, PLATFORMS
from .coordinator import ProtectSensorsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to the current version.

    v1 -> v2: the unique id changed from ``host`` to ``host:port`` so that two
    consoles on the same host can coexist. Rewrite existing unique ids so the
    duplicate-prevention check keeps matching after an upgrade.
    """
    if entry.version == 1:
        host = entry.data.get("host")
        port = entry.data.get("port", DEFAULT_PORT)
        new_unique_id = f"{host}:{port}" if host else entry.unique_id
        hass.config_entries.async_update_entry(
            entry, unique_id=new_unique_id, version=2
        )
        _LOGGER.debug("Migrated config entry to v2 (unique_id=%s)", new_unique_id)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UniFi Protect Sensors from a config entry."""
    coordinator = ProtectSensorsCoordinator(hass, entry)

    # async_config_entry_first_refresh raises ConfigEntryNotReady on failure;
    # let it propagate directly so the original error message is preserved.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        # The first refresh already started the background WebSocket task; if
        # platform setup fails (or is cancelled) HA will not call
        # async_unload_entry, so tear the coordinator (and its WS task) down
        # here to avoid leaking it. BaseException also covers CancelledError.
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await coordinator.async_shutdown()
        raise

    # Reload the entry when options change so runtime settings (verify_ssl) apply.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a UniFi Protect Sensors config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ProtectSensorsCoordinator | None = hass.data[DOMAIN].pop(
            entry.entry_id, None
        )
        if coordinator is not None:
            await coordinator.async_shutdown()
    return unload_ok
