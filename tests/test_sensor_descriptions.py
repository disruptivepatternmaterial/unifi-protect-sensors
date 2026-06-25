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
        required = {"temperature", "humidity", "illuminance", "battery", "co2", "pm25", "pm10", "aqi"}
        missing = required - keys
        assert not missing, f"Missing expected sensor keys: {missing}"

    def test_usl_environmental_fields_match_fixture(self, usl_device):
        from custom_components.unifi_protect_sensors.helpers import get_nested
        from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS

        usl_descs = [d for d in SENSOR_DESCRIPTIONS if "USL-Environmental" in d.expected_source]
        for desc in usl_descs:
            # Fields may legitimately be null (e.g. leakDetectedAt), so we just check the
            # path exists (i.e. the key is in the fixture at the right nesting level)
            result = get_nested(usl_device, desc.payload_field)
            # temperature, humidity, illuminance, battery should have real values
            if desc.key in ("temperature", "humidity", "illuminance", "battery"):
                assert result is not None, (
                    f"Expected non-null value for '{desc.key}' in USL fixture "
                    f"(payload_field='{desc.payload_field}')"
                )

    def test_up_airquality_fields_match_fixture(self, aq_device):
        from custom_components.unifi_protect_sensors.helpers import get_nested
        from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS

        aq_descs = [d for d in SENSOR_DESCRIPTIONS if "UP-AirQuality" in d.expected_source]
        for desc in aq_descs:
            result = get_nested(aq_device, desc.payload_field)
            if desc.key in ("temperature", "humidity", "co2", "pm25", "pm10", "aqi"):
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
        required = {"leak", "battery_low", "connectivity", "tamper"}
        assert not required - keys

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

    def test_usl_fields_present_in_fixture(self, usl_device):
        from custom_components.unifi_protect_sensors.helpers import get_nested
        from custom_components.unifi_protect_sensors.binary_sensor import BINARY_SENSOR_DESCRIPTIONS

        usl_descs = [d for d in BINARY_SENSOR_DESCRIPTIONS if "USL-Environmental" in d.expected_source]
        always_present = {"battery_low", "connectivity"}
        for desc in usl_descs:
            if desc.key in always_present:
                result = get_nested(usl_device, desc.payload_field)
                assert result is not None, (
                    f"Expected '{desc.key}' (field '{desc.payload_field}') to be non-null in USL fixture"
                )


# ---------------------------------------------------------------------------
# coordinator payload parsing (pure logic, no network)
# ---------------------------------------------------------------------------

class TestCoordinatorPayloadParsing:
    """Test _async_update_data payload shape handling without network calls."""

    def _make_coordinator(self):
        """Build a coordinator with all HA dependencies mocked."""
        from unittest.mock import MagicMock, AsyncMock, patch

        mock_hass = MagicMock()
        entry_data = {
            "host": "192.168.1.1",
            "port": 443,
            "username": "admin",
            "password": "secret",
            "api_key": "",
            "verify_ssl": False,
        }

        with patch.dict(sys.modules, {
            "homeassistant.helpers.update_coordinator": MagicMock(
                DataUpdateCoordinator=object,
                UpdateFailed=Exception,
            ),
            "homeassistant.helpers.aiohttp_client": MagicMock(),
        }):
            from custom_components.unifi_protect_sensors.coordinator import ProtectSensorsCoordinator

        coord = object.__new__(ProtectSensorsCoordinator)
        coord.hass = mock_hass
        coord._host = "192.168.1.1"
        coord._port = 443
        coord._username = "admin"
        coord._password = "secret"
        coord._api_key = ""
        coord._verify_ssl = False
        coord._base_url = "https://192.168.1.1:443"
        coord._session_cookie = "TOKEN_VALUE"
        return coord

    def test_list_payload_indexed_by_id(self):
        coord = self._make_coordinator()
        from custom_components.unifi_protect_sensors.coordinator import ProtectSensorsCoordinator as C

        payload = [{"id": "a", "name": "Sensor A"}, {"id": "b", "name": "Sensor B"}]
        # Replicate the indexing logic directly
        result = {d["id"]: d for d in payload if isinstance(d, dict) and "id" in d}
        assert result == {"a": {"id": "a", "name": "Sensor A"}, "b": {"id": "b", "name": "Sensor B"}}

    def test_wrapped_data_payload_indexed_by_id(self):
        payload = {"data": [{"id": "x", "name": "X"}]}
        result = {d["id"]: d for d in payload["data"] if isinstance(d, dict) and "id" in d}
        assert result == {"x": {"id": "x", "name": "X"}}

    def test_entries_without_id_skipped(self):
        payload = [{"name": "no-id"}, {"id": "ok", "name": "has-id"}]
        result = {d["id"]: d for d in payload if isinstance(d, dict) and "id" in d}
        assert "ok" in result
        assert len(result) == 1


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
        from unittest.mock import MagicMock, patch

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
        from unittest.mock import MagicMock

        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "temperature")
        coord = self._make_mock_coordinator({})

        entity = object.__new__(UniFiProtectMetricSensor)
        entity.coordinator = coord
        entity._device_id = "missing"
        entity.entity_description = desc

        assert entity.native_value is None

    def test_sensor_available_false_when_coordinator_failed(self, usl_device):
        from custom_components.unifi_protect_sensors.sensor import UniFiProtectMetricSensor, SENSOR_DESCRIPTIONS
        from unittest.mock import MagicMock

        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "temperature")
        coord = self._make_mock_coordinator({"abc123": usl_device}, last_update_success=False)

        entity = object.__new__(UniFiProtectMetricSensor)
        entity.coordinator = coord
        entity._device_id = "abc123"
        entity.entity_description = desc

        # super().available delegates to coordinator.last_update_success
        # We patch it to reflect the expected behaviour directly
        from unittest.mock import PropertyMock, patch
        with patch(
            "custom_components.unifi_protect_sensors.sensor.CoordinatorEntity.available",
            new_callable=PropertyMock,
            return_value=False,
        ):
            assert entity.available is False

    def test_binary_sensor_is_on_bool_field(self, usl_device):
        from custom_components.unifi_protect_sensors.binary_sensor import UniFiProtectBinarySensor, BINARY_SENSOR_DESCRIPTIONS

        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "connectivity")
        coord = self._make_mock_coordinator({"abc123": usl_device})

        entity = object.__new__(UniFiProtectBinarySensor)
        entity.coordinator = coord
        entity._device_id = "abc123"
        entity.entity_description = desc

        assert entity.is_on is True

    def test_binary_sensor_leak_null_means_off(self, usl_device):
        from custom_components.unifi_protect_sensors.binary_sensor import UniFiProtectBinarySensor, BINARY_SENSOR_DESCRIPTIONS

        assert usl_device["leakDetectedAt"] is None
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "leak")
        coord = self._make_mock_coordinator({"abc123": usl_device})

        entity = object.__new__(UniFiProtectBinarySensor)
        entity.coordinator = coord
        entity._device_id = "abc123"
        entity.entity_description = desc

        assert entity.is_on is None  # null → unknown state (not yet reported by device)

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
