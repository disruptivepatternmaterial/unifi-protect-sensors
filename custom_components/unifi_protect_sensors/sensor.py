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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProtectSensorsCoordinator
from .helpers import get_nested

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ProtectSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with Protect-specific metadata."""

    payload_field: str
    expected_source: str = ""


SENSOR_DESCRIPTIONS: tuple[ProtectSensorEntityDescription, ...] = (
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
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="nox_index",
        translation_key="nox_index",
        payload_field="stats.nox.value",
        expected_source="UP-AirQuality",
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
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from coordinator data."""
    coordinator: ProtectSensorsCoordinator = hass.data[DOMAIN][entry.entry_id]
    dev_reg = dr.async_get(hass)
    entities: list[UniFiProtectMetricSensor] = []

    for device_id, device in coordinator.data.items():
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            name=device.get("name", device_id),
            model=device.get("type") or device.get("modelKey"),
            manufacturer="Ubiquiti",
        )
        device_type: str = (device.get("type") or device.get("modelKey") or "").strip()
        for description in SENSOR_DESCRIPTIONS:
            # Only create entities whose expected_source includes this device's type.
            # An empty expected_source means the description applies to all devices.
            sources = [s.strip() for s in description.expected_source.split(",") if s.strip()]
            if sources and not any(s.lower() in device_type.lower() or device_type.lower() in s.lower() for s in sources):
                continue
            # Only create if the field is actually present in this device's payload.
            # This avoids ghost entities for unsupported readings.
            if get_nested(device, description.payload_field) is None:
                continue
            entities.append(UniFiProtectMetricSensor(coordinator, device_id, description))

    async_add_entities(entities)


class UniFiProtectMetricSensor(CoordinatorEntity[ProtectSensorsCoordinator], SensorEntity):
    """A UniFi Protect metric sensor backed by the coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProtectSensorsCoordinator,
        device_id: str,
        description: ProtectSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, device_id)}}

    @property
    def native_value(self) -> Any | None:
        device = self.coordinator.data.get(self._device_id)
        if device is None:
            return None
        return get_nested(device, self.entity_description.payload_field)

    @property
    def available(self) -> bool:
        return super().available and self._device_id in self.coordinator.data

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
