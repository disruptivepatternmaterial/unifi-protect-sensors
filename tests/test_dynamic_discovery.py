"""Tests for dynamic entity discovery in the sensor/binary_sensor platforms.

These exercise async_setup_entry's discovery callback without a live HA runtime,
relying on the stubs installed by conftest.py.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parents[1]))


class _FakeCoordinator:
    """Minimal coordinator: holds data and fans out to registered listeners."""

    def __init__(self, data: dict) -> None:
        self.data = data
        self.last_update_success = True
        self._listeners: list = []

    def async_add_listener(self, update_callback, context=None):
        self._listeners.append(update_callback)
        return lambda: self._listeners.remove(update_callback)

    def notify(self) -> None:
        for cb in list(self._listeners):
            cb()


def _make_hass_entry(coordinator):
    from custom_components.unifi_protect_sensors.const import DOMAIN

    entry = MagicMock()
    entry.entry_id = "entry1"
    hass = MagicMock()
    hass.data = {DOMAIN: {"entry1": coordinator}}
    return hass, entry


class TestSensorDiscovery:
    async def test_initial_devices_create_entities(self, two_device_payload):
        from custom_components.unifi_protect_sensors import sensor

        coord = _FakeCoordinator(dict(two_device_payload))
        hass, entry = _make_hass_entry(coord)
        added: list = []

        await sensor.async_setup_entry(hass, entry, lambda ents: added.extend(ents))

        assert added, "expected entities for the two seeded devices"
        # Every entity has a unique id and they are distinct.
        uids = [e._attr_unique_id for e in added]
        assert len(uids) == len(set(uids))

    async def test_discovery_is_idempotent(self, two_device_payload):
        from custom_components.unifi_protect_sensors import sensor

        coord = _FakeCoordinator(dict(two_device_payload))
        hass, entry = _make_hass_entry(coord)
        added: list = []

        await sensor.async_setup_entry(hass, entry, lambda ents: added.extend(ents))
        first_count = len(added)

        # Subsequent coordinator updates must not re-add existing entities.
        coord.notify()
        coord.notify()
        assert len(added) == first_count

    async def test_new_device_added_after_setup(self, two_device_payload, aq_device):
        from custom_components.unifi_protect_sensors import sensor

        coord = _FakeCoordinator(dict(two_device_payload))
        hass, entry = _make_hass_entry(coord)
        added: list = []

        await sensor.async_setup_entry(hass, entry, lambda ents: added.extend(ents))
        first_count = len(added)

        new_dev = copy.deepcopy(aq_device)
        new_dev["id"] = "late-adopted"
        coord.data["late-adopted"] = new_dev
        coord.notify()

        assert len(added) > first_count
        new_uids = [e._attr_unique_id for e in added[first_count:]]
        assert all(uid.startswith("late-adopted_") for uid in new_uids)


class TestBinarySensorDiscovery:
    async def test_initial_and_idempotent(self, two_device_payload):
        from custom_components.unifi_protect_sensors import binary_sensor

        coord = _FakeCoordinator(dict(two_device_payload))
        hass, entry = _make_hass_entry(coord)
        added: list = []

        await binary_sensor.async_setup_entry(hass, entry, lambda ents: added.extend(ents))
        first_count = len(added)
        assert first_count > 0

        coord.notify()
        assert len(added) == first_count
