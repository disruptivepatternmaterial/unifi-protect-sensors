"""Tests for the shared entity base and platform discovery."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

COMPONENT_DIR = Path(__file__).parents[1] / "custom_components" / "unifi_protect_sensors"


class _FakeCoordinator:
    def __init__(self, data: dict) -> None:
        self.data = data
        self.last_update_success = True


def _sensor(device_id: str, coordinator, key: str = "temperature"):
    from custom_components.unifi_protect_sensors.sensor import (
        SENSOR_DESCRIPTIONS,
        UniFiProtectMetricSensor,
    )

    description = next(d for d in SENSOR_DESCRIPTIONS if d.key == key)
    return UniFiProtectMetricSensor(coordinator, device_id, description)


class TestDeviceInfo:
    def test_named_device_uses_its_name(self, usl_device):
        entity = _sensor("abc123", _FakeCoordinator({"abc123": usl_device}))
        assert entity._attr_device_info["name"] == "Environmental Sensor"
        assert entity._attr_device_info["model"] == "USL-Environmental-US"

    def test_null_name_falls_back_to_device_id(self, usl_device):
        """Protect sends name=null for a device that has never been named."""
        device = {**usl_device, "name": None}
        entity = _sensor("abc123", _FakeCoordinator({"abc123": device}))
        assert entity._attr_device_info["name"] == "abc123"

    def test_missing_name_falls_back_to_device_id(self, usl_device):
        device = {k: v for k, v in usl_device.items() if k != "name"}
        entity = _sensor("abc123", _FakeCoordinator({"abc123": device}))
        assert entity._attr_device_info["name"] == "abc123"

    def test_model_falls_back_to_modelkey(self, usl_device):
        device = {**usl_device, "type": None}
        entity = _sensor("abc123", _FakeCoordinator({"abc123": device}))
        assert entity._attr_device_info["model"] == "sensor"

    def test_unique_id_combines_device_and_key(self, usl_device):
        entity = _sensor("abc123", _FakeCoordinator({"abc123": usl_device}))
        assert entity._attr_unique_id == "abc123_temperature"


class TestBinarySensorState:
    def _binary(self, device_id, coordinator, key):
        from custom_components.unifi_protect_sensors.binary_sensor import (
            BINARY_SENSOR_DESCRIPTIONS,
            UniFiProtectBinarySensor,
        )

        description = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == key)
        return UniFiProtectBinarySensor(coordinator, device_id, description)

    def test_null_timestamp_is_clear(self, usl_device):
        device = {**usl_device, "leakDetectedAt": None}
        entity = self._binary("abc123", _FakeCoordinator({"abc123": device}), "leak")
        assert entity.is_on is False

    def test_timestamp_present_is_detected(self, usl_device):
        device = {**usl_device, "leakDetectedAt": 1735689600000}
        entity = self._binary("abc123", _FakeCoordinator({"abc123": device}), "leak")
        assert entity.is_on is True

    def test_missing_device_is_unknown_not_clear(self, usl_device):
        """A device that left the snapshot is unknown; reporting "clear" would
        fabricate a reading the sensor never sent."""
        entity = self._binary("abc123", _FakeCoordinator({"abc123": usl_device}), "leak")
        entity.coordinator.data = {}
        assert entity.is_on is None

    def test_tristate_field_stays_unknown_when_null(self, usl_device):
        device = copy.deepcopy(usl_device)
        device["batteryStatus"]["isLow"] = None
        entity = self._binary("abc123", _FakeCoordinator({"abc123": device}), "battery_low")
        assert entity.is_on is None


class TestAvailability:
    def test_available_when_connected(self, usl_device):
        assert _sensor("abc123", _FakeCoordinator({"abc123": usl_device})).available is True

    def test_unavailable_when_disconnected(self, usl_device):
        device = {**usl_device, "state": "DISCONNECTED"}
        assert _sensor("abc123", _FakeCoordinator({"abc123": device})).available is False

    def test_unknown_state_stays_available(self, usl_device):
        """Transient/unknown states must not flap entities to unavailable."""
        device = {**usl_device, "state": "SOMETHING_NEW"}
        assert _sensor("abc123", _FakeCoordinator({"abc123": device})).available is True

    def test_unavailable_when_device_left_the_snapshot(self, usl_device):
        entity = _sensor("abc123", _FakeCoordinator({"abc123": usl_device}))
        entity.coordinator.data = {}
        assert entity.available is False


class TestZeroValuesArePreserved:
    def test_zero_reading_is_reported_not_dropped(self, aq_device):
        """A sensor reporting 0 is real data, not a missing reading."""
        device = copy.deepcopy(aq_device)
        device["airQuality"]["co2"]["value"] = 0
        entity = _sensor("def456", _FakeCoordinator({"def456": device}), "co2")
        assert entity.native_value == 0


class TestTranslationsStayInSync:
    def test_en_json_matches_strings_json(self):
        """translations/en.json is a copy of strings.json; drift means a config
        flow step renders as a raw key in the UI."""
        strings = json.loads((COMPONENT_DIR / "strings.json").read_text())
        english = json.loads((COMPONENT_DIR / "translations" / "en.json").read_text())
        assert strings == english

    def test_every_translation_key_has_a_name(self):
        from custom_components.unifi_protect_sensors.binary_sensor import (
            BINARY_SENSOR_DESCRIPTIONS,
        )
        from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS

        strings = json.loads((COMPONENT_DIR / "strings.json").read_text())
        entity_names = strings["entity"]
        for platform, descriptions in (
            ("sensor", SENSOR_DESCRIPTIONS),
            ("binary_sensor", BINARY_SENSOR_DESCRIPTIONS),
        ):
            for description in descriptions:
                assert description.translation_key in entity_names[platform], (
                    f"{platform}.{description.key} has no name in strings.json"
                )
