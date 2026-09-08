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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BATTERY_MODELS, ENVIRONMENTAL_MODELS, MODEL_UP_AIRQUALITY
from .entity import ProtectDescriptionMixin, ProtectEntity, async_setup_protect_platform

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ProtectBinarySensorEntityDescription(ProtectDescriptionMixin, BinarySensorEntityDescription):
    """Describes one boolean reading exposed by a Protect sensor device."""

    # For timestamp-style fields (e.g. leakDetectedAt) a null value is a
    # definitive "clear" reading, not "unknown", so map None -> off.
    null_means_off: bool = False


BINARY_SENSOR_DESCRIPTIONS: tuple[ProtectBinarySensorEntityDescription, ...] = (
    ProtectBinarySensorEntityDescription(
        key="leak",
        translation_key="leak",
        # Protect uses a nullable timestamp (leakDetectedAt) not a boolean flag
        payload_field="leakDetectedAt",
        device_types=ENVIRONMENTAL_MODELS,
        device_class=BinarySensorDeviceClass.MOISTURE,
        null_means_off=True,
    ),
    ProtectBinarySensorEntityDescription(
        key="battery_low",
        translation_key="battery_low",
        payload_field="batteryStatus.isLow",
        device_types=BATTERY_MODELS,
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ProtectBinarySensorEntityDescription(
        key="tamper",
        translation_key="tamper",
        # Protect uses a nullable timestamp (tamperingDetectedAt) not a boolean flag
        payload_field="tamperingDetectedAt",
        device_types=ENVIRONMENTAL_MODELS,
        device_class=BinarySensorDeviceClass.TAMPER,
        null_means_off=True,
    ),
    ProtectBinarySensorEntityDescription(
        key="vape_detected",
        translation_key="vape_detected",
        # Non-zero vape index means vape detected; 0 means clear
        payload_field="airQuality.vape.value",
        device_types=(MODEL_UP_AIRQUALITY,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities, including devices that appear after startup."""
    async_setup_protect_platform(
        hass,
        entry,
        async_add_entities,
        descriptions=BINARY_SENSOR_DESCRIPTIONS,
        build_entity=UniFiProtectBinarySensor,
        logger=_LOGGER,
    )


class UniFiProtectBinarySensor(ProtectEntity, BinarySensorEntity):
    """A UniFi Protect binary sensor backed by the coordinator."""

    entity_description: ProtectBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        device = self._device
        if device is None:
            # The device left the snapshot entirely; that is unknown, not "clear".
            return None
        value = self._payload_value
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
