"""Test configuration and shared fixtures for UniFi Protect Sensors."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Minimal Home Assistant stubs (used when homeassistant is not installed)
# ---------------------------------------------------------------------------

def _install_ha_stubs() -> None:
    """Always inject stubs — unit tests must not depend on a live HA install."""
    """Inject dataclass-compatible HA stubs into sys.modules.

    When homeassistant is not installed we create lightweight stand-ins that
    mirror the class hierarchy used by the component code so that tests can
    import and exercise the pure-Python logic without a running HA instance.
    """

    # --- EntityCategory ---
    class EntityCategory:
        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    # --- EntityDescription (mirrors homeassistant.helpers.entity.EntityDescription) ---
    @dataclass(frozen=True, kw_only=True)
    class EntityDescription:
        key: str
        translation_key: str | None = None
        device_class: Any = None
        entity_category: Any = None
        entity_registry_enabled_default: bool = True
        entity_registry_visible_default: bool = True
        force_update: bool = False
        icon: str | None = None
        has_entity_name: bool = False
        name: Any = None
        translation_placeholders: Any = None
        unit_of_measurement: str | None = None

    # --- Sensor stubs ---
    class SensorDeviceClass:
        TEMPERATURE = "temperature"
        HUMIDITY = "humidity"
        ILLUMINANCE = "illuminance"
        BATTERY = "battery"
        CO2 = "carbon_dioxide"
        PM25 = "pm25"
        PM10 = "pm10"
        AQI = "aqi"

    class SensorStateClass:
        MEASUREMENT = "measurement"
        TOTAL = "total"
        TOTAL_INCREASING = "total_increasing"

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription(EntityDescription):
        native_unit_of_measurement: str | None = None
        state_class: Any = None
        suggested_display_precision: int | None = None
        suggested_unit_of_measurement: str | None = None
        last_reset: Any = None

    class SensorEntity:
        pass

    # --- Binary sensor stubs ---
    class BinarySensorDeviceClass:
        MOISTURE = "moisture"
        BATTERY = "battery"
        CONNECTIVITY = "connectivity"
        TAMPER = "tamper"

    @dataclass(frozen=True, kw_only=True)
    class BinarySensorEntityDescription(EntityDescription):
        pass

    class BinarySensorEntity:
        pass

    # --- CoordinatorEntity (simplified) ---
    class CoordinatorEntity:
        """Stub for homeassistant.helpers.update_coordinator.CoordinatorEntity."""

        def __class_getitem__(cls, item):
            return cls

        def __init__(self, coordinator):
            self.coordinator = coordinator

        @property
        def available(self) -> bool:
            return self.coordinator.last_update_success

    # --- DataUpdateCoordinator / UpdateFailed ---
    class DataUpdateCoordinator:
        """Stub for homeassistant.helpers.update_coordinator.DataUpdateCoordinator."""

        # Support generic alias syntax: DataUpdateCoordinator[SomeType]
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, *, name, update_interval):
            self.hass = hass
            self._logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data: dict = {}
            self.last_update_success: bool = True

    class UpdateFailed(Exception):
        pass

    class ConfigEntryNotReady(Exception):
        pass

    # --- HomeAssistant const stubs ---
    class UnitOfTemperature:
        CELSIUS = "°C"
        FAHRENHEIT = "°F"

    # --- Wire up sys.modules stubs ---
    ha_const = MagicMock()
    ha_const.PERCENTAGE = "%"
    ha_const.LIGHT_LUX = "lx"
    ha_const.CONCENTRATION_PARTS_PER_MILLION = "ppm"
    ha_const.CONCENTRATION_MICROGRAMS_PER_CUBIC_METER = "µg/m³"
    ha_const.UnitOfTemperature = UnitOfTemperature

    sensor_mod = MagicMock()
    sensor_mod.SensorDeviceClass = SensorDeviceClass
    sensor_mod.SensorStateClass = SensorStateClass
    sensor_mod.SensorEntityDescription = SensorEntityDescription
    sensor_mod.SensorEntity = SensorEntity

    binary_mod = MagicMock()
    binary_mod.BinarySensorDeviceClass = BinarySensorDeviceClass
    binary_mod.BinarySensorEntityDescription = BinarySensorEntityDescription
    binary_mod.BinarySensorEntity = BinarySensorEntity

    coordinator_mod = MagicMock()
    coordinator_mod.DataUpdateCoordinator = DataUpdateCoordinator
    coordinator_mod.UpdateFailed = UpdateFailed
    coordinator_mod.CoordinatorEntity = CoordinatorEntity

    entity_mod = MagicMock()
    entity_mod.EntityCategory = EntityCategory

    exceptions_mod = MagicMock()
    exceptions_mod.ConfigEntryNotReady = ConfigEntryNotReady

    ha_core = MagicMock()
    ha_core.HomeAssistant = MagicMock
    ha_core.callback = lambda fn: fn  # passthrough decorator

    stubs: dict[str, Any] = {
        "homeassistant": MagicMock(),
        "homeassistant.core": ha_core,
        "homeassistant.config_entries": MagicMock(),
        "homeassistant.exceptions": exceptions_mod,
        "homeassistant.const": ha_const,
        "homeassistant.components": MagicMock(),
        "homeassistant.components.sensor": sensor_mod,
        "homeassistant.components.binary_sensor": binary_mod,
        "homeassistant.helpers": MagicMock(),
        "homeassistant.helpers.update_coordinator": coordinator_mod,
        "homeassistant.helpers.entity": entity_mod,
        "homeassistant.helpers.entity_platform": MagicMock(),
        "homeassistant.helpers.device_registry": MagicMock(),
        "homeassistant.helpers.aiohttp_client": MagicMock(),
    }
    sys.modules.update(stubs)


_install_ha_stubs()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def load_fixture(filename: str) -> dict:
    """Load a JSON fixture from tests/fixtures/."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with fixture_path.open() as f:
        return json.load(f)


@pytest.fixture
def usl_device() -> dict:
    return load_fixture("usl_environmental.json")


@pytest.fixture
def aq_device() -> dict:
    return load_fixture("up_airquality.json")


@pytest.fixture
def two_device_payload(usl_device, aq_device) -> dict:
    return {usl_device["id"]: usl_device, aq_device["id"]: aq_device}
