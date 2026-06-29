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
from .helpers import device_type_matches, field_exists, get_nested

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ProtectSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with Protect-specific metadata."""

    payload_field: str
    expected_source: str = ""


SENSOR_DESCRIPTIONS: tuple[ProtectSensorEntityDescription, ...] = (
    # ── UFP-SENSE / USL-Environmental-US sensors (stats.* fields) ──────────
    ProtectSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        payload_field="stats.temperature.value",
        expected_source="UFP-SENSE, USL-Environmental-US",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ProtectSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        payload_field="stats.humidity.value",
        expected_source="UFP-SENSE, USL-Environmental-US",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ProtectSensorEntityDescription(
        key="illuminance",
        translation_key="illuminance",
        payload_field="stats.light.value",
        expected_source="UFP-SENSE, USL-Environmental-US",
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
        expected_source="UFP-SENSE, USL-Environmental-US, USL-Entry-US",
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
        expected_source="UP-AirQuality",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ProtectSensorEntityDescription(
        key="aq_humidity",
        translation_key="humidity",
        payload_field="airQuality.humidity.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ProtectSensorEntityDescription(
        key="co2",
        translation_key="co2",
        payload_field="airQuality.co2.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm1",
        translation_key="pm1",
        payload_field="airQuality.pm1p0.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM1,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm25",
        translation_key="pm25",
        payload_field="airQuality.pm2p5.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm4",
        translation_key="pm4",
        payload_field="airQuality.pm4p0.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM4,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="pm10",
        translation_key="pm10",
        payload_field="airQuality.pm10p0.value",
        expected_source="UP-AirQuality",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM10,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="voc_index",
        translation_key="voc_index",
        payload_field="airQuality.voc.value",
        expected_source="UP-AirQuality",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="aqi",
        translation_key="aqi",
        payload_field="airQuality.aqi.value",
        expected_source="UP-AirQuality",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ProtectSensorEntityDescription(
        key="vape_index",
        translation_key="vape_index",
        payload_field="airQuality.vape.value",
        expected_source="UP-AirQuality",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from coordinator data, including devices that
    appear after startup (e.g. a newly adopted sensor)."""
    coordinator: ProtectSensorsCoordinator = hass.data[DOMAIN][entry.entry_id]
    dev_reg = dr.async_get(hass)
    known_devices: set[str] = set()
    known_entities: set[str] = set()

    @callback
    def _discover_entities() -> None:
        # This runs inside the coordinator's listener loop on every update, so a
        # failure here must never propagate (it would drop the WebSocket / skip
        # sibling entity updates). Swallow and retry on the next update.
        try:
            new_entities: list[UniFiProtectMetricSensor] = []
            for device_id, device in list(coordinator.data.items()):
                device_type: str = (device.get("type") or device.get("modelKey") or "").strip()
                if device_id not in known_devices:
                    dev_reg.async_get_or_create(
                        config_entry_id=entry.entry_id,
                        identifiers={(DOMAIN, device_id)},
                        name=device.get("name", device_id),
                        model=device.get("type") or device.get("modelKey"),
                        manufacturer="Ubiquiti",
                    )
                    known_devices.add(device_id)
                for description in SENSOR_DESCRIPTIONS:
                    if not device_type_matches(device_type, description.expected_source):
                        continue
                    # Create the entity only when the field key exists in the payload.
                    # We use key-existence (not value truthiness) so entities survive
                    # temporarily-null readings (e.g. a sensor that is rebooting).
                    if not field_exists(device, description.payload_field):
                        continue
                    unique_id = f"{device_id}_{description.key}"
                    if unique_id in known_entities:
                        continue
                    known_entities.add(unique_id)
                    new_entities.append(
                        UniFiProtectMetricSensor(coordinator, device_id, description)
                    )
            if new_entities:
                async_add_entities(new_entities)
        except Exception:  # noqa: BLE001 - discovery must not break the coordinator loop
            _LOGGER.exception("Sensor entity discovery failed; will retry on next update")

    _discover_entities()
    # Re-run discovery on every coordinator update so newly adopted devices (or
    # fields that only appear once a sensor comes online) get their entities.
    entry.async_on_unload(coordinator.async_add_listener(_discover_entities))


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
