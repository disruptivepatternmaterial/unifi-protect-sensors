"""Sensor entities for UniFi Protect Sensors."""
from __future__ import annotations
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

from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class ProtectSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with Protect-specific metadata."""

    # Dot-separated path into the Protect sensor payload (confirmed via fixtures)
    payload_field: str
    # Which device(s) expose this metric
    expected_source: str = ""


SENSOR_DESCRIPTIONS: tuple[ProtectSensorEntityDescription, ...] = (
    # ── USL-Environmental ────────────────────────────────────────────────────
    ProtectSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        payload_field="stats.temperature.value",
        expected_source="USL-Environmental, UP-AirQuality",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ProtectSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        payload_field="stats.humidity.value",
        expected_source="USL-Environmental, UP-AirQuality",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ProtectSensorEntityDescription(
        key="illuminance",
        translation_key="illuminance",
        payload_field="stats.light.value",
        expected_source="USL-Environmental",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="battery",
        translation_key="battery",
        payload_field="batteryStatus.percentage",
        expected_source="USL-Environmental",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── UP-AirQuality ─────────────────────────────────────────────────────────
    # NOTE: payload_field paths below are PROVISIONAL and will be confirmed
    # once real sanitized fixtures are captured from an actual UP-AirQuality device.
    ProtectSensorEntityDescription(
        key="co2",
        translation_key="co2",
        payload_field="stats.co2.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm1",
        translation_key="pm1",
        payload_field="stats.pm1.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm25",
        translation_key="pm25",
        payload_field="stats.pm25.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm4",
        translation_key="pm4",
        payload_field="stats.pm4.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm10",
        translation_key="pm10",
        payload_field="stats.pm10.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM10,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="voc_index",
        translation_key="voc_index",
        payload_field="stats.voc.value",
        expected_source="UP-AirQuality",
        # VOC index (1-500) — not a mass concentration; no unit or device class
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="nox_index",
        translation_key="nox_index",
        payload_field="stats.nox.value",
        expected_source="UP-AirQuality",
        # NOx index (1-500) — not a mass concentration; no unit or device class
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="aqi",
        translation_key="aqi",
        payload_field="stats.aqi.value",
        expected_source="UP-AirQuality",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="vape_index",
        translation_key="vape_index",
        payload_field="stats.vape.value",
        expected_source="UP-AirQuality",
        # Vape index (0-100) — unitless index value
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities (populated once coordinator is wired up)."""
    async_add_entities([])


class UniFiProtectMetricSensor(SensorEntity):
    """A UniFi Protect metric sensor backed by parsed Protect data."""

    _attr_has_entity_name = True

    def __init__(
        self,
        unique_device_id: str,
        description: ProtectSensorEntityDescription,
        value: Any | None = None,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._attr_unique_id = f"{unique_device_id}_{description.key}"
        self._value = value

    @property
    def native_value(self) -> Any | None:
        """Return the sensor value."""
        return self._value

    def update_value(self, value: Any | None) -> None:
        """Update value and push HA state."""
        self._value = value
        self.async_write_ha_state()
