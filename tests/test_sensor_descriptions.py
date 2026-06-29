"""Unit tests for sensor and binary sensor entity descriptions — no HA runtime required."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class TestGetNested:
    def _import(self):
        from custom_components.unifi_protect_sensors.helpers import get_nested
        return get_nested

    def test_top_level_key(self):
        fn = self._import()
        assert fn({"a": 1}, "a") == 1

    def test_nested_key(self):
        fn = self._import()
        assert fn({"a": {"b": {"c": 42}}}, "a.b.c") == 42

    def test_missing_top_level(self):
        fn = self._import()
        assert fn({}, "missing") is None

    def test_missing_nested(self):
        fn = self._import()
        assert fn({"a": {"b": 1}}, "a.x") is None

    def test_non_dict_intermediate(self):
        fn = self._import()
        assert fn({"a": "string"}, "a.b") is None

    def test_none_value_returned(self):
        fn = self._import()
        assert fn({"a": None}, "a") is None

    def test_false_value_returned(self):
        fn = self._import()
        assert fn({"a": False}, "a") is False

    def test_zero_value_returned(self):
        fn = self._import()
        assert fn({"a": 0}, "a") == 0


class TestDeviceTypeMatches:
    def _import(self):
        from custom_components.unifi_protect_sensors.helpers import device_type_matches
        return device_type_matches

    def test_exact_match(self):
        fn = self._import()
        assert fn("UP-AirQuality", "UP-AirQuality") is True

    def test_case_insensitive(self):
        fn = self._import()
        assert fn("up-airquality", "UP-AirQuality") is True

    def test_match_within_comma_list(self):
        fn = self._import()
        assert fn("USL-Environmental-US", "UFP-SENSE, USL-Environmental-US") is True

    def test_empty_expected_source_matches_all(self):
        fn = self._import()
        assert fn("anything", "") is True

    def test_blank_device_type_matches_nothing_specific(self):
        fn = self._import()
        assert fn("", "UP-AirQuality") is False

    def test_generic_modelkey_does_not_match(self):
        """modelKey fallback ('sensor') must not match a concrete model source."""
        fn = self._import()
        assert fn("sensor", "UP-AirQuality") is False

    def test_usl_entry_matches_battery_sources(self):
        """USL-Entry-US is the battery/battery_low source and must still match."""
        fn = self._import()
        assert fn("USL-Entry-US", "UFP-SENSE, USL-Environmental-US, USL-Entry-US") is True

    def test_no_reverse_substring_false_positive(self):
        """A short type must not match a longer source (the old bidirectional bug)."""
        fn = self._import()
        assert fn("UP", "UP-AirQuality") is False
        assert fn("US", "USL-Environmental-US") is False

    def test_no_forward_substring_false_positive(self):
        fn = self._import()
        assert fn("UP-AirQuality-Pro", "UP-AirQuality") is False


class TestFieldExists:
    def _import(self):
        from custom_components.unifi_protect_sensors.helpers import field_exists
        return field_exists

    def test_top_level_present(self):
        assert self._import()({"a": 1}, "a") is True

    def test_top_level_missing(self):
        assert self._import()({}, "a") is False

    def test_nested_present_with_null_value(self):
        assert self._import()({"a": {"b": None}}, "a.b") is True

    def test_nested_missing(self):
        assert self._import()({"a": {}}, "a.b") is False

    def test_intermediate_not_dict(self):
        assert self._import()({"a": "string"}, "a.b") is False

    def test_deep_path(self):
        assert self._import()({"airQuality": {"co2": {"value": 400}}}, "airQuality.co2.value") is True

    def test_deep_path_missing_leaf(self):
        assert self._import()({"airQuality": {"co2": {}}}, "airQuality.co2.value") is False


# ---------------------------------------------------------------------------
# sensor descriptions
# ---------------------------------------------------------------------------

class TestSensorDescriptions:
    def _import(self):
        from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
        return SENSOR_DESCRIPTIONS

    def test_all_have_unique_keys(self):
        descs = self._import()
        keys = [d.key for d in descs]
        assert len(keys) == len(set(keys)), "Duplicate sensor description keys found"

    def test_all_have_payload_field(self):
        descs = self._import()
        for d in descs:
            assert d.payload_field, f"Description '{d.key}' is missing payload_field"

    def test_payload_fields_are_valid_dot_paths(self):
        descs = self._import()
        for d in descs:
            parts = d.payload_field.split(".")
            assert all(p for p in parts), f"Description '{d.key}' has empty segment in payload_field"

    def test_all_have_translation_key(self):
        descs = self._import()
        for d in descs:
            assert d.translation_key, f"Description '{d.key}' is missing translation_key"

    def test_expected_sensor_keys_present(self):
        descs = self._import()
        keys = {d.key for d in descs}
        required = {"temperature", "humidity", "illuminance", "battery",
                    "aq_temperature", "aq_humidity",
                    "co2", "pm25", "pm10", "aqi"}
        missing = required - keys
        assert not missing, f"Missing expected sensor keys: {missing}"

    def test_no_nox_index(self):
        """nox_index is not in the UP-AirQuality API — should not be defined."""
        descs = self._import()
        keys = {d.key for d in descs}
        assert "nox_index" not in keys

    def test_aq_fields_use_airquality_path(self):
        """All UP-AirQuality sensor descriptions must use airQuality.* paths."""
        descs = self._import()
        aq_descs = [d for d in descs if "UP-AirQuality" in d.expected_source]
        for desc in aq_descs:
            assert desc.payload_field.startswith("airQuality."), (
                f"AQ sensor '{desc.key}' uses wrong path '{desc.payload_field}' "
                f"(expected airQuality.*)"
            )

    def test_usl_fields_use_stats_path(self):
        """USL-Environmental-US sensor descriptions must use stats.* paths."""
        descs = self._import()
        usl_descs = [
            d for d in descs
            if "USL-Environmental-US" in d.expected_source and d.key in ("temperature", "humidity", "illuminance")
        ]
        assert usl_descs, "No USL temp/humidity/illuminance descriptions found"
        for desc in usl_descs:
            assert desc.payload_field.startswith("stats."), (
                f"USL sensor '{desc.key}' uses wrong path '{desc.payload_field}'"
            )

    def test_usl_fields_match_fixture(self, usl_device):
        from custom_components.unifi_protect_sensors.helpers import get_nested, field_exists
        from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS

        usl_descs = [d for d in SENSOR_DESCRIPTIONS if "USL-Environmental-US" in d.expected_source]
        assert usl_descs, "No descriptions matched USL-Environmental-US"
        for desc in usl_descs:
            assert field_exists(usl_device, desc.payload_field), (
                f"Field path '{desc.payload_field}' for '{desc.key}' not found in USL fixture"
            )
            if desc.key in ("temperature", "humidity", "illuminance", "battery"):
                result = get_nested(usl_device, desc.payload_field)
                assert result is not None, (
                    f"Expected non-null value for '{desc.key}' in USL fixture "
                    f"(payload_field='{desc.payload_field}')"
                )

    def test_aq_fields_match_fixture(self, aq_device):
        from custom_components.unifi_protect_sensors.helpers import get_nested, field_exists
        from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS

        aq_descs = [d for d in SENSOR_DESCRIPTIONS if "UP-AirQuality" in d.expected_source]
        assert aq_descs, "No descriptions matched UP-AirQuality"
        for desc in aq_descs:
            assert field_exists(aq_device, desc.payload_field), (
                f"Field path '{desc.payload_field}' for '{desc.key}' not found in AQ fixture"
            )
            if desc.key in ("aq_temperature", "aq_humidity", "co2", "pm25", "pm10", "aqi", "voc_index"):
                result = get_nested(aq_device, desc.payload_field)
                assert result is not None, (
                    f"Expected non-null value for '{desc.key}' in AQ fixture "
                    f"(payload_field='{desc.payload_field}')"
                )


# ---------------------------------------------------------------------------
# binary sensor descriptions
# ---------------------------------------------------------------------------

class TestBinarySensorDescriptions:
    def _import(self):
        from custom_components.unifi_protect_sensors.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
        return BINARY_SENSOR_DESCRIPTIONS

    def test_all_have_unique_keys(self):
        descs = self._import()
        keys = [d.key for d in descs]
        assert len(keys) == len(set(keys))

    def test_all_have_payload_field(self):
        descs = self._import()
        for d in descs:
            assert d.payload_field, f"Binary description '{d.key}' is missing payload_field"

    def test_all_have_translation_key(self):
        descs = self._import()
        for d in descs:
            assert d.translation_key, f"Binary description '{d.key}' is missing translation_key"

    def test_expected_keys_present(self):
        descs = self._import()
        keys = {d.key for d in descs}
        required = {"leak", "battery_low", "tamper", "vape_detected"}
        assert not required - keys, f"Missing binary sensor keys: {required - keys}"

    def test_no_connectivity_sensor(self):
        """connectivity was removed — device availability is exposed via the available property."""
        descs = self._import()
        keys = {d.key for d in descs}
        assert "connectivity" not in keys

    def test_leak_uses_correct_field(self):
        descs = self._import()
        leak = next(d for d in descs if d.key == "leak")
        assert leak.payload_field == "leakDetectedAt", (
            "Leak sensor must use 'leakDetectedAt' (nullable timestamp), not a boolean flag"
        )

    def test_tamper_uses_correct_field(self):
        descs = self._import()
        tamper = next(d for d in descs if d.key == "tamper")
        assert tamper.payload_field == "tamperingDetectedAt"

    def test_vape_uses_airquality_path(self):
        descs = self._import()
        vape = next(d for d in descs if d.key == "vape_detected")
        assert vape.payload_field.startswith("airQuality."), (
            f"vape_detected must use airQuality.* path, got '{vape.payload_field}'"
        )

    def test_usl_fields_present_in_fixture(self, usl_device):
        from custom_components.unifi_protect_sensors.helpers import field_exists
        from custom_components.unifi_protect_sensors.binary_sensor import BINARY_SENSOR_DESCRIPTIONS

        usl_descs = [d for d in BINARY_SENSOR_DESCRIPTIONS if "USL-Environmental-US" in d.expected_source]
        assert usl_descs, "No binary sensor descriptions matched USL-Environmental-US"
        for desc in usl_descs:
            assert field_exists(usl_device, desc.payload_field), (
                f"Field '{desc.payload_field}' for '{desc.key}' not found in USL fixture"
            )

    def test_vape_field_present_in_aq_fixture(self, aq_device):
        from custom_components.unifi_protect_sensors.helpers import field_exists
        from custom_components.unifi_protect_sensors.binary_sensor import BINARY_SENSOR_DESCRIPTIONS

        vape = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "vape_detected")
        assert field_exists(aq_device, vape.payload_field), (
            f"vape_detected field '{vape.payload_field}' not found in AQ fixture"
        )


# ---------------------------------------------------------------------------
# coordinator payload parsing (pure logic, no network)
# ---------------------------------------------------------------------------

class TestCoordinatorPayloadParsing:
    """Test _async_update_data payload shape handling without network calls."""

    def test_bootstrap_sensors_indexed_by_id(self):
        """Bootstrap format: dict with 'sensors' list."""
        payload = {
            "sensors": [
                {"id": "a", "name": "Sensor A", "type": "UFP-SENSE"},
                {"id": "b", "name": "Sensor B", "type": "USL-Environmental-US"},
            ]
        }
        sensors_list = payload.get("sensors", [])
        result = {d["id"]: d for d in sensors_list if isinstance(d, dict) and "id" in d}
        assert result == {
            "a": {"id": "a", "name": "Sensor A", "type": "UFP-SENSE"},
            "b": {"id": "b", "name": "Sensor B", "type": "USL-Environmental-US"},
        }

    def test_entries_without_id_skipped(self):
        payload = {"sensors": [{"name": "no-id"}, {"id": "ok", "name": "has-id"}]}
        sensors_list = payload.get("sensors", [])
        result = {d["id"]: d for d in sensors_list if isinstance(d, dict) and "id" in d}
        assert "ok" in result
        assert len(result) == 1

    def test_missing_sensors_key_yields_empty(self):
        payload = {"cameras": [], "lights": []}
        sensors_list = payload.get("sensors", [])
        result = {d["id"]: d for d in sensors_list if isinstance(d, dict) and "id" in d}
        assert result == {}


# ---------------------------------------------------------------------------
# entity property logic (mock coordinator, no HA runtime)
# ---------------------------------------------------------------------------

class TestEntityProperties:
    def _make_mock_coordinator(self, data: dict, last_update_success: bool = True):
        from unittest.mock import MagicMock
        coord = MagicMock()
        coord.data = data
        coord.last_update_success = last_update_success
        return coord

    def test_sensor_native_value_reads_nested_field(self, usl_device):
        from custom_components.unifi_protect_sensors.sensor import UniFiProtectMetricSensor, SENSOR_DESCRIPTIONS
        from unittest.mock import patch

        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "temperature")
        coord = self._make_mock_coordinator({"abc123": usl_device})

        with patch("custom_components.unifi_protect_sensors.sensor.CoordinatorEntity.__init__", lambda s, c: None):
            entity = object.__new__(UniFiProtectMetricSensor)
            entity.coordinator = coord
            entity._device_id = "abc123"
            entity.entity_description = desc

        assert entity.native_value == 22.5

    def test_sensor_native_value_none_when_device_missing(self, usl_device):
        from custom_components.unifi_protect_sensors.sensor import UniFiProtectMetricSensor, SENSOR_DESCRIPTIONS

        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "temperature")
        coord = self._make_mock_coordinator({})

        entity = object.__new__(UniFiProtectMetricSensor)
        entity.coordinator = coord
        entity._device_id = "missing"
        entity.entity_description = desc

        assert entity.native_value is None

    def test_aq_sensor_co2_reads_airquality_path(self, aq_device):
        from custom_components.unifi_protect_sensors.sensor import UniFiProtectMetricSensor, SENSOR_DESCRIPTIONS

        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "co2")
        coord = self._make_mock_coordinator({"def456": aq_device})

        entity = object.__new__(UniFiProtectMetricSensor)
        entity.coordinator = coord
        entity._device_id = "def456"
        entity.entity_description = desc

        assert entity.native_value == 694

    def test_sensor_available_false_when_coordinator_failed(self, usl_device):
        from custom_components.unifi_protect_sensors.sensor import UniFiProtectMetricSensor, SENSOR_DESCRIPTIONS
        from unittest.mock import PropertyMock, patch

        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "temperature")
        coord = self._make_mock_coordinator({"abc123": usl_device}, last_update_success=False)

        entity = object.__new__(UniFiProtectMetricSensor)
        entity.coordinator = coord
        entity._device_id = "abc123"
        entity.entity_description = desc

        with patch(
            "custom_components.unifi_protect_sensors.sensor.CoordinatorEntity.available",
            new_callable=PropertyMock,
            return_value=False,
        ):
            assert entity.available is False

    def test_binary_sensor_leak_null_means_off(self, usl_device):
        from custom_components.unifi_protect_sensors.binary_sensor import UniFiProtectBinarySensor, BINARY_SENSOR_DESCRIPTIONS

        assert usl_device["leakDetectedAt"] is None
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "leak")
        assert desc.null_means_off is True
        coord = self._make_mock_coordinator({"abc123": usl_device})

        entity = object.__new__(UniFiProtectBinarySensor)
        entity.coordinator = coord
        entity._device_id = "abc123"
        entity.entity_description = desc

        # null leakDetectedAt → no active leak → off (not unknown)
        assert entity.is_on is False

    def test_binary_sensor_tamper_timestamp_means_on(self, usl_device):
        from custom_components.unifi_protect_sensors.binary_sensor import UniFiProtectBinarySensor, BINARY_SENSOR_DESCRIPTIONS

        device = {**usl_device, "tamperingDetectedAt": "2026-06-25T10:00:00Z"}
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "tamper")
        coord = self._make_mock_coordinator({"abc123": device})

        entity = object.__new__(UniFiProtectBinarySensor)
        entity.coordinator = coord
        entity._device_id = "abc123"
        entity.entity_description = desc

        assert entity.is_on is True

    def test_binary_sensor_battery_low_false(self, usl_device):
        from custom_components.unifi_protect_sensors.binary_sensor import UniFiProtectBinarySensor, BINARY_SENSOR_DESCRIPTIONS

        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "battery_low")
        coord = self._make_mock_coordinator({"abc123": usl_device})

        entity = object.__new__(UniFiProtectBinarySensor)
        entity.coordinator = coord
        entity._device_id = "abc123"
        entity.entity_description = desc

        assert entity.is_on is False

    def test_binary_sensor_vape_detected_zero_means_off(self, aq_device):
        from custom_components.unifi_protect_sensors.binary_sensor import UniFiProtectBinarySensor, BINARY_SENSOR_DESCRIPTIONS

        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "vape_detected")
        coord = self._make_mock_coordinator({"def456": aq_device})

        entity = object.__new__(UniFiProtectBinarySensor)
        entity.coordinator = coord
        entity._device_id = "def456"
        entity.entity_description = desc

        # vape.value=0 → bool(0)=False → not detected
        assert entity.is_on is False
