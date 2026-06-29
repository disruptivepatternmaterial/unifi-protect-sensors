"""Binary sensor entities for UniFi Protect Sensors."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProtectSensorsCoordinator
from .helpers import device_type_matches, field_exists, get_nested

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ProtectBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extends BinarySensorEntityDescription with Protect-specific metadata."""

    payload_field: str
    expected_source: str = ""
    # For timestamp-style fields (e.g. leakDetectedAt) a null value is a
    # definitive "clear" reading, not "unknown", so map None -> off.
    null_means_off: bool = False


BINARY_SENSOR_DESCRIPTIONS: tuple[ProtectBinarySensorEntityDescription, ...] = (
    ProtectBinarySensorEntityDescription(
        key="leak",
        translation_key="leak",
        # Protect uses a nullable timestamp (leakDetectedAt) not a boolean flag
        payload_field="leakDetectedAt",
        expected_source="UFP-SENSE, USL-Environmental-US",
        device_class=BinarySensorDeviceClass.MOISTURE,
        null_means_off=True,
    ),
    ProtectBinarySensorEntityDescription(
        key="battery_low",
        translation_key="battery_low",
        payload_field="batteryStatus.isLow",
        expected_source="UFP-SENSE, USL-Environmental-US, USL-Entry-US",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ProtectBinarySensorEntityDescription(
        key="tamper",
        translation_key="tamper",
        # Protect uses a nullable timestamp (tamperingDetectedAt) not a boolean flag
        payload_field="tamperingDetectedAt",
        expected_source="UFP-SENSE, USL-Environmental-US",
        device_class=BinarySensorDeviceClass.TAMPER,
        null_means_off=True,
    ),
    ProtectBinarySensorEntityDescription(
        key="vape_detected",
        translation_key="vape_detected",
        # Non-zero vape index means vape detected; 0 means clear
        payload_field="airQuality.vape.value",
        expected_source="UP-AirQuality",
        device_class=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from coordinator data, including devices
    that appear after startup (e.g. a newly adopted sensor)."""
    coordinator: ProtectSensorsCoordinator = hass.data[DOMAIN][entry.entry_id]
    dev_reg = dr.async_get(hass)
    known_devices: set[str] = set()
    known_entities: set[str] = set()

    @callback
    def _discover_entities() -> None:
        # Runs in the coordinator listener loop on every update; never let a
        # failure propagate and disrupt the WebSocket / other listeners.
        try:
            new_entities: list[UniFiProtectBinarySensor] = []
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
                for description in BINARY_SENSOR_DESCRIPTIONS:
                    if not device_type_matches(device_type, description.expected_source):
                        continue
                    # Check key existence (not value), so entities survive null readings.
                    if not field_exists(device, description.payload_field):
                        continue
                    unique_id = f"{device_id}_{description.key}"
                    if unique_id in known_entities:
                        continue
                    known_entities.add(unique_id)
                    new_entities.append(
                        UniFiProtectBinarySensor(coordinator, device_id, description)
                    )
            if new_entities:
                async_add_entities(new_entities)
        except Exception:  # noqa: BLE001 - discovery must not break the coordinator loop
            _LOGGER.exception("Binary sensor entity discovery failed; will retry on next update")

    _discover_entities()
    entry.async_on_unload(coordinator.async_add_listener(_discover_entities))


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
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def is_on(self) -> bool | None:
        device = self.coordinator.data.get(self._device_id)
        if device is None:
            return None
        value = get_nested(device, self.entity_description.payload_field)
        if value is None:
            # Timestamp fields report null when the event is clear; treat that as
            # off. Genuinely tri-state fields (e.g. batteryStatus.isLow) leave the
            # flag unset and stay unknown when null.
            return False if self.entity_description.null_means_off else None
        if isinstance(value, bool):
            return value
        # Timestamp fields (leakDetectedAt, tamperingDetectedAt) are truthy when
        # an event is active.
        return bool(value)

    @property
    def available(self) -> bool:
        device = self.coordinator.data.get(self._device_id)
        if not (super().available and device is not None):
            return False
        # Only an explicit DISCONNECTED marks the device unavailable; unknown or
        # transient states stay available to avoid flapping on stale snapshots.
        return device.get("state") != "DISCONNECTED"

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
