"""Tests for config-entry migration (async_migrate_entry)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parents[1]))


def _make_entry(version: int, data: dict, unique_id: str | None):
    entry = MagicMock()
    entry.version = version
    entry.data = data
    entry.unique_id = unique_id
    return entry


class TestAsyncMigrateEntry:
    async def test_v1_to_v2_sets_host_port_unique_id(self):
        from custom_components.unifi_protect_sensors import async_migrate_entry

        entry = _make_entry(1, {"host": "192.168.1.50", "port": 7443}, "192.168.1.50")
        hass = MagicMock()

        result = await async_migrate_entry(hass, entry)

        assert result is True
        hass.config_entries.async_update_entry.assert_called_once()
        _, kwargs = hass.config_entries.async_update_entry.call_args
        assert kwargs["unique_id"] == "192.168.1.50:7443"
        assert kwargs["version"] == 2

    async def test_v1_default_port_when_missing(self):
        from custom_components.unifi_protect_sensors import async_migrate_entry

        entry = _make_entry(1, {"host": "console.local"}, "console.local")
        hass = MagicMock()

        await async_migrate_entry(hass, entry)

        _, kwargs = hass.config_entries.async_update_entry.call_args
        assert kwargs["unique_id"] == "console.local:443"

    async def test_v2_is_noop(self):
        from custom_components.unifi_protect_sensors import async_migrate_entry

        entry = _make_entry(2, {"host": "h", "port": 443}, "h:443")
        hass = MagicMock()

        result = await async_migrate_entry(hass, entry)

        assert result is True
        hass.config_entries.async_update_entry.assert_not_called()
