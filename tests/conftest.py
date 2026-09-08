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
        PM1 = "pm1"
        PM25 = "pm25"
        PM4 = "pm4"
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

        def __init__(self, hass, logger, *, name, update_interval, config_entry=None):
            self.hass = hass
            self._logger = logger
            self.name = name
            self.update_interval = update_interval
            self.config_entry = config_entry
            self.data: dict = {}
            self.last_update_success: bool = True

    class UpdateFailed(Exception):
        pass

    class ConfigEntryNotReady(Exception):
        pass

    class ConfigEntryAuthFailed(Exception):
        pass

    # --- HomeAssistant const stubs ---
    class UnitOfTemperature:
        CELSIUS = "°C"
        FAHRENHEIT = "°F"

    # --- Wire up sys.modules stubs ---
    ha_const = MagicMock()
    # Real values: these are config-entry storage keys, so the tests must use the
    # same strings Home Assistant does.
    ha_const.CONF_HOST = "host"
    ha_const.CONF_PORT = "port"
    ha_const.CONF_USERNAME = "username"
    ha_const.CONF_PASSWORD = "password"
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
    # DeviceInfo is a TypedDict in Home Assistant, so calling it yields a plain dict.
    entity_mod.DeviceInfo = dict

    exceptions_mod = MagicMock()
    exceptions_mod.ConfigEntryNotReady = ConfigEntryNotReady
    exceptions_mod.ConfigEntryAuthFailed = ConfigEntryAuthFailed

    ha_core = MagicMock()
    ha_core.HomeAssistant = MagicMock
    ha_core.callback = lambda fn: fn  # passthrough decorator

    # --- Config / options flow stubs ---
    # Real base classes (not MagicMocks) so the flow modules are importable and
    # each step's return value can be asserted on.
    class _FlowBase:
        def __init_subclass__(cls, **kwargs) -> None:  # absorbs `domain=...`
            super().__init_subclass__()

        def async_show_form(self, **kwargs) -> dict:
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs) -> dict:
            return {"type": "create_entry", **kwargs}

        def async_abort(self, **kwargs) -> dict:
            return {"type": "abort", **kwargs}

        async def async_set_unique_id(self, unique_id) -> None:
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self) -> None:
            return None

    class ConfigFlow(_FlowBase):
        pass

    class OptionsFlow(_FlowBase):
        pass

    config_entries_mod = MagicMock()
    config_entries_mod.ConfigFlow = ConfigFlow
    config_entries_mod.OptionsFlow = OptionsFlow

    # --- aiohttp stub (WSMsgType used in coordinator.py) ---
    # Prefer the real package: the exception classes must be genuine so that
    # `except (aiohttp.ClientError, ...)` in the config flow is exercised for real.
    try:
        import aiohttp  # noqa: F401
    except ImportError:
        import enum

        class _WSMsgType(enum.IntEnum):
            BINARY = 2
            TEXT = 1
            CLOSE = 8
            CLOSING = 9
            CLOSED = 10
            ERROR = 258

        aiohttp_stub = MagicMock()
        aiohttp_stub.WSMsgType = _WSMsgType
        aiohttp_stub.WSServerHandshakeError = type("WSServerHandshakeError", (Exception,), {"status": None})
        sys.modules["aiohttp"] = aiohttp_stub

    stubs: dict[str, Any] = {
        "homeassistant": MagicMock(),
        "homeassistant.core": ha_core,
        "homeassistant.config_entries": config_entries_mod,
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

    # `from homeassistant import config_entries` resolves the attribute on the
    # parent package before consulting sys.modules, so a submodule stub that is
    # only registered in sys.modules would be silently bypassed. Mirror every
    # stub onto its parent so both import styles reach the same object.
    for dotted, module in stubs.items():
        parent_name, _, attribute = dotted.rpartition(".")
        if parent_name:
            setattr(stubs[parent_name], attribute, module)


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
