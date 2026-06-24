"""Unit tests for sensor entity descriptions — no HA runtime required."""
from __future__ import annotations
import sys
from pathlib import Path

# Allow importing the custom component without a full HA install
sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest


def test_all_sensor_descriptions_have_keys():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    for desc in SENSOR_DESCRIPTIONS:
        assert desc.key, f"Sensor description missing key: {desc}"


def test_all_binary_sensor_descriptions_have_keys():
    from custom_components.unifi_protect_sensors.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
    for desc in BINARY_SENSOR_DESCRIPTIONS:
        assert desc.key, f"Binary sensor description missing key: {desc}"


def test_sensor_unique_keys():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    keys = [d.key for d in SENSOR_DESCRIPTIONS]
    assert len(keys) == len(set(keys)), "Duplicate sensor description keys"


def test_binary_sensor_unique_keys():
    from custom_components.unifi_protect_sensors.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
    keys = [d.key for d in BINARY_SENSOR_DESCRIPTIONS]
    assert len(keys) == len(set(keys)), "Duplicate binary sensor description keys"


def test_all_descriptions_have_payload_field():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    from custom_components.unifi_protect_sensors.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
    for desc in SENSOR_DESCRIPTIONS:
        assert desc.payload_field, f"Missing payload_field on sensor {desc.key}"
    for desc in BINARY_SENSOR_DESCRIPTIONS:
        assert desc.payload_field, f"Missing payload_field on binary_sensor {desc.key}"


def test_voc_index_has_no_unit():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    voc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "voc_index")
    assert voc.native_unit_of_measurement is None, (
        "VOC index must not be given a concentration unit"
    )


def test_nox_index_has_no_unit():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    nox = next(d for d in SENSOR_DESCRIPTIONS if d.key == "nox_index")
    assert nox.native_unit_of_measurement is None, (
        "NOx index must not be given a concentration unit"
    )


def test_vape_index_has_no_unit():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    vape = next(d for d in SENSOR_DESCRIPTIONS if d.key == "vape_index")
    assert vape.native_unit_of_measurement is None, "Vape index must not be given a unit"


def test_all_pm_use_ugm3():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    for key in ("pm1", "pm25", "pm4", "pm10"):
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == key)
        assert desc.native_unit_of_measurement == CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, (
            f"{key} must use µg/m³"
        )


def test_co2_uses_ppm():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION
    co2 = next(d for d in SENSOR_DESCRIPTIONS if d.key == "co2")
    assert co2.native_unit_of_measurement == CONCENTRATION_PARTS_PER_MILLION


def test_temperature_uses_celsius():
    from custom_components.unifi_protect_sensors.sensor import SENSOR_DESCRIPTIONS
    from homeassistant.const import UnitOfTemperature
    temp = next(d for d in SENSOR_DESCRIPTIONS if d.key == "temperature")
    assert temp.native_unit_of_measurement == UnitOfTemperature.CELSIUS


def test_leak_binary_is_moisture():
    from custom_components.unifi_protect_sensors.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass
    leak = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "leak")
    assert leak.device_class == BinarySensorDeviceClass.MOISTURE


def test_fixture_usl_environmental_has_expected_stats():
    from tests.conftest import load_fixture
    payload = load_fixture("usl_environmental.json")
    assert "stats" in payload
    assert "temperature" in payload["stats"]
    assert "humidity" in payload["stats"]
    assert "light" in payload["stats"]
    assert "batteryStatus" in payload


def test_fixture_up_airquality_has_expected_stats():
    from tests.conftest import load_fixture
    payload = load_fixture("up_airquality.json")
    assert "stats" in payload
    for key in ("temperature", "humidity", "co2", "pm25", "aqi", "voc", "nox", "vape"):
        assert key in payload["stats"], f"Missing key '{key}' in UP-AirQuality fixture stats"
