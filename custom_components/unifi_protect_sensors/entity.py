"""Shared entity plumbing for the sensor and binary_sensor platforms.

Both platforms map a dot-separated bootstrap payload path onto a Home Assistant
entity, and both must discover devices that appear after startup. That shape is
described once here — ``ProtectDescriptionMixin`` for the metadata, ``ProtectEntity``
for the entity itself, and ``async_setup_protect_platform`` for discovery — so the
platform modules only declare *which* readings they expose.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from logging import Logger
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, STATE_DISCONNECTED
from .coordinator import ProtectSensorsCoordinator
from .helpers import field_exists, get_nested


@dataclass(frozen=True, kw_only=True)
class ProtectDescriptionMixin:
    """Protect-specific metadata shared by both entity description types."""

    payload_field: str
    # Protect model identifiers this reading exists on. Empty matches every model.
    device_types: tuple[str, ...] = ()

    def supports(self, device_type: str) -> bool:
        """Return True if a device of ``device_type`` exposes this reading.

        Matching is exact (case-insensitive) against Protect's model identifier, so
        an unrecognised or blank device type gets no entities rather than all of
        them, and overlapping model names cannot cross-match.
        """
        if not self.device_types:
            return True
        device_type = device_type.strip().casefold()
        return any(device_type == model.casefold() for model in self.device_types)


class ProtectEntity(CoordinatorEntity[ProtectSensorsCoordinator]):
    """Base for entities backed by one field of one Protect device snapshot."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProtectSensorsCoordinator,
        device_id: str,
        description: ProtectDescriptionMixin,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{description.key}"

        device = coordinator.data.get(device_id) or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            # Protect sends a null name for a device that has never been named.
            name=device.get("name") or device_id,
            model=device.get("type") or device.get("modelKey"),
            manufacturer=MANUFACTURER,
        )

    @property
    def _device(self) -> dict[str, Any] | None:
        """The current snapshot for this device, or None if it left the payload."""
        return self.coordinator.data.get(self._device_id)

    @property
    def _payload_value(self) -> Any:
        """This entity's raw reading, or None when the device or field is absent."""
        device = self._device
        if device is None:
            return None
        return get_nested(device, self.entity_description.payload_field)

    @property
    def available(self) -> bool:
        device = self._device
        if not (super().available and device is not None):
            return False
        # Only an explicit DISCONNECTED marks the device unavailable; unknown or
        # transient states stay available to avoid flapping on stale snapshots.
        return device.get("state") != STATE_DISCONNECTED


def async_setup_protect_platform(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    *,
    descriptions: Iterable[ProtectDescriptionMixin],
    build_entity: Callable[[ProtectSensorsCoordinator, str, Any], ProtectEntity],
    logger: Logger,
) -> None:
    """Create entities for the current snapshot and for devices seen later.

    Discovery re-runs on every coordinator update so a newly adopted sensor — or a
    field that only appears once a device comes online — is picked up without a
    reload.
    """
    coordinator: ProtectSensorsCoordinator = hass.data[DOMAIN][entry.entry_id]
    descriptions = tuple(descriptions)
    known_entities: set[str] = set()

    @callback
    def _discover_entities() -> None:
        # This runs inside the coordinator's listener loop, so a failure here must
        # never propagate: it would drop the WebSocket and skip sibling entity
        # updates. Swallow it and retry on the next update.
        try:
            new_entities: list[ProtectEntity] = []
            for device_id, device in list(coordinator.data.items()):
                device_type = str(device.get("type") or device.get("modelKey") or "")
                for description in descriptions:
                    unique_id = f"{device_id}_{description.key}"
                    if unique_id in known_entities:
                        continue
                    if not description.supports(device_type):
                        continue
                    # Key existence, not value truthiness, so entities survive a
                    # temporarily-null reading (e.g. a sensor that is rebooting).
                    if not field_exists(device, description.payload_field):
                        continue
                    known_entities.add(unique_id)
                    new_entities.append(build_entity(coordinator, device_id, description))
            if new_entities:
                async_add_entities(new_entities)
        except Exception:  # noqa: BLE001 - discovery must not break the coordinator loop
            logger.exception("Entity discovery failed; will retry on the next update")

    _discover_entities()
    entry.async_on_unload(coordinator.async_add_listener(_discover_entities))
