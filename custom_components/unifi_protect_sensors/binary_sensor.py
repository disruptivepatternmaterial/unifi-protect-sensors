"""Binary sensor entities for UniFi Protect Sensors."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProtectSensorsCoordinator
from .helpers import get_nested

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ProtectBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extends BinarySensorEntityDescription with Protect-specific metadata."""

    payload_field: str
    expected_source: str = ""


BINARY_SENSOR_DESCRIPTIONS: tuple[ProtectBinarySensorEntityDescription, ...] = (
    ProtectBinarySensorEntityDescription(
        key="leak",
        translation_key="leak",
        # Protect uses a nullable timestamp (leakDetectedAt) not a boolean flag
        payload_field="leakDetectedAt",
        expected_source="USL-Environmental",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    ProtectBinarySensorEntityDescription(
        key="battery_low",
        translation_key="battery_low",
        payload_field="batteryStatus.isLow",
        expected_source="USL-Environmental",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ProtectBinarySensorEntityDescription(
        key="connectivity",
        translation_key="connectivity",
        payload_field="isConnected",
        expected_source="USL-Environmental, UP-AirQuality",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ProtectBinarySensorEntityDescription(
        key="tamper",
        translation_key="tamper",
        # Protect uses a nullable timestamp (tamperingDetectedAt) not a boolean flag
        payload_field="tamperingDetectedAt",
        expected_source="USL-Environmental",
        device_class=BinarySensorDeviceClass.TAMPER,
    ),
    ProtectBinarySensorEntityDescription(
        key="vape_detected",
        translation_key="vape_detected",
        payload_field="stats.vapeDetected",
        expected_source="UP-AirQuality",
        device_class=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from coordinator data."""
    coordinator: ProtectSensorsCoordinator = hass.data[DOMAIN][entry.entry_id]
    dev_reg = dr.async_get(hass)
    entities: list[UniFiProtectBinarySensor] = []

    for device_id, device in coordinator.data.items():
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            name=device.get("name", device_id),
            model=device.get("type") or device.get("modelKey"),
            manufacturer="Ubiquiti",
        )
        device_type: str = (device.get("type") or device.get("modelKey") or "").strip()
        for description in BINARY_SENSOR_DESCRIPTIONS:
            # Only create entities whose expected_source includes this device's type.
            sources = [s.strip() for s in description.expected_source.split(",") if s.strip()]
            if sources and not any(s.lower() in device_type.lower() or device_type.lower() in s.lower() for s in sources):
                continue
            # For timestamp-based fields (leak, tamper), the key being present in the
            # payload (even as null) means the device supports it. Check key existence
            # rather than value truthiness.
            field_parts = description.payload_field.split(".")
            container = device
            for part in field_parts[:-1]:
                container = container.get(part, {}) if isinstance(container, dict) else {}
            if not isinstance(container, dict) or field_parts[-1] not in container:
                continue
            entities.append(UniFiProtectBinarySensor(coordinator, device_id, description))

    async_add_entities(entities)


class UniFiProtectBinarySensor(CoordinatorEntity[ProtectSensorsCoordinator], BinarySensorEntity):
    """A UniFi Protect binary sensor backed by the coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProtectSensorsCoordinator,
        device_id: str,
        description: ProtectBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, device_id)}}

    @property
    def is_on(self) -> bool | None:
        device = self.coordinator.data.get(self._device_id)
        if device is None:
            return None
        value = get_nested(device, self.entity_description.payload_field)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        # Timestamp fields (leakDetectedAt, tamperingDetectedAt) are truthy when
        # an event is active, null/None when clear.
        return bool(value)

    @property
    def available(self) -> bool:
        return super().available and self._device_id in self.coordinator.data

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
