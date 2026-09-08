"""Sensor entities for UniFi Protect Sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BATTERY_MODELS,
    ENVIRONMENTAL_MODELS,
    MODEL_UP_AIRQUALITY,
)
from .entity import ProtectDescriptionMixin, ProtectEntity, async_setup_protect_platform

_LOGGER = logging.getLogger(__name__)

_AIRQUALITY_ONLY = (MODEL_UP_AIRQUALITY,)


@dataclass(frozen=True, kw_only=True)
class ProtectSensorEntityDescription(ProtectDescriptionMixin, SensorEntityDescription):
    """Describes one numeric reading exposed by a Protect sensor device."""


SENSOR_DESCRIPTIONS: tuple[ProtectSensorEntityDescription, ...] = (
    # ── UFP-SENSE / USL-Environmental-US sensors (stats.* fields) ──────────
    ProtectSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        payload_field="stats.temperature.value",
        device_types=ENVIRONMENTAL_MODELS,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ProtectSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        payload_field="stats.humidity.value",
        device_types=ENVIRONMENTAL_MODELS,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ProtectSensorEntityDescription(
        key="illuminance",
        translation_key="illuminance",
        payload_field="stats.light.value",
        device_types=ENVIRONMENTAL_MODELS,
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Battery applies to all battery-powered devices; wired devices (UP-AirQuality)
    # report percentage=null so they are naturally excluded by the null-value filter.
    ProtectSensorEntityDescription(
        key="battery",
        translation_key="battery",
        payload_field="batteryStatus.percentage",
        device_types=BATTERY_MODELS,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── UP-AirQuality sensors (airQuality.* fields) ─────────────────────────
    # Temperature and humidity on UP-AirQuality live in airQuality.*, not stats.*
    ProtectSensorEntityDescription(
        key="aq_temperature",
        translation_key="temperature",
        payload_field="airQuality.temperature.value",
        device_types=_AIRQUALITY_ONLY,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ProtectSensorEntityDescription(
        key="aq_humidity",
        translation_key="humidity",
        payload_field="airQuality.humidity.value",
        device_types=_AIRQUALITY_ONLY,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ProtectSensorEntityDescription(
        key="co2",
        translation_key="co2",
        payload_field="airQuality.co2.value",
        device_types=_AIRQUALITY_ONLY,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm1",
        translation_key="pm1",
        payload_field="airQuality.pm1p0.value",
        device_types=_AIRQUALITY_ONLY,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM1,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm25",
        translation_key="pm25",
        payload_field="airQuality.pm2p5.value",
        device_types=_AIRQUALITY_ONLY,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm4",
        translation_key="pm4",
        payload_field="airQuality.pm4p0.value",
        device_types=_AIRQUALITY_ONLY,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM4,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm10",
        translation_key="pm10",
        payload_field="airQuality.pm10p0.value",
        device_types=_AIRQUALITY_ONLY,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM10,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="voc_index",
        translation_key="voc_index",
        payload_field="airQuality.voc.value",
        device_types=_AIRQUALITY_ONLY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="aqi",
        translation_key="aqi",
        payload_field="airQuality.aqi.value",
        device_types=_AIRQUALITY_ONLY,
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="vape_index",
        translation_key="vape_index",
        payload_field="airQuality.vape.value",
        device_types=_AIRQUALITY_ONLY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities, including devices that appear after startup."""
    async_setup_protect_platform(
        hass,
        entry,
        async_add_entities,
        descriptions=SENSOR_DESCRIPTIONS,
        build_entity=UniFiProtectMetricSensor,
        logger=_LOGGER,
    )


class UniFiProtectMetricSensor(ProtectEntity, SensorEntity):
    """A UniFi Protect metric sensor backed by the coordinator."""

    entity_description: ProtectSensorEntityDescription

    @property
    def native_value(self) -> Any:
        return self._payload_value
