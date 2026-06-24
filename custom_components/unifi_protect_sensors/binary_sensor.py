"""Binary sensor entities for UniFi Protect Sensors."""
from __future__ import annotations
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

from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class ProtectBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extends BinarySensorEntityDescription with Protect-specific metadata."""

    payload_field: str
    expected_source: str = ""


BINARY_SENSOR_DESCRIPTIONS: tuple[ProtectBinarySensorEntityDescription, ...] = (
    # ── USL-Environmental ────────────────────────────────────────────────────
    ProtectBinarySensorEntityDescription(
        key="leak",
        translation_key="leak",
        payload_field="isLeakDetected",
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
        payload_field="tamperingDetectedAt",
        expected_source="USL-Environmental",
        device_class=BinarySensorDeviceClass.TAMPER,
    ),
    # ── UP-AirQuality ─────────────────────────────────────────────────────────
    # Vape detection binary — payload_field is provisional until fixtures confirm
    # whether Protect exposes a boolean detection flag distinct from the vape index.
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
    """Set up binary sensor entities (populated once coordinator is wired up)."""
    async_add_entities([])


class UniFiProtectBinarySensor(BinarySensorEntity):
    """A UniFi Protect binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        unique_device_id: str,
        description: ProtectBinarySensorEntityDescription,
        is_on: bool | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        self.entity_description = description
        self._attr_unique_id = f"{unique_device_id}_{description.key}"
        self._is_on = is_on

    @property
    def is_on(self) -> bool | None:
        """Return state."""
        return self._is_on

    def update_state(self, is_on: bool | None) -> None:
        """Update state and push HA state."""
        self._is_on = is_on
        self.async_write_ha_state()
