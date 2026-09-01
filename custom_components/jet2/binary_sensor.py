"""Binary sensor platform for the Jet2 integration."""

from typing import Any, override

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BOOKING_REFERENCE, DOMAIN
from .coordinator import Jet2ConfigEntry, Jet2Coordinator

SENSOR_TYPES = (
    BinarySensorEntityDescription(
        key="isTradeBooking",
        name="Is Trade Booking",
        icon="mdi:briefcase",
    ),
    BinarySensorEntityDescription(
        key="hasResortFlightCheckIn",
        name="Has Resort Flight Check-in",
        icon="mdi:airplane-check",
    ),
    BinarySensorEntityDescription(
        key="checkInStatus",
        name="Check-In Allowed",
        icon="mdi:airplane-check",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Jet2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Jet2 binary sensors."""
    coordinator = entry.runtime_data
    booking = coordinator.data["data"]
    async_add_entities(
        Jet2BinarySensor(
            coordinator,
            entry.data[CONF_BOOKING_REFERENCE],
            description,
        )
        for description in SENSOR_TYPES
        if description.key in booking
    )


class Jet2BinarySensor(CoordinatorEntity[Jet2Coordinator], BinarySensorEntity):
    """Represent a boolean value from a Jet2 booking."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Jet2Coordinator,
        booking_reference: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{DOMAIN}-{booking_reference}-{description.key}-binary".lower()
        )
        booking = coordinator.data["data"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, booking_reference)},
            manufacturer="Jet2",
            model=booking.get("holidayType"),
            name=booking_reference.upper(),
            configuration_url="https://github.com/jampez77/Jet2/",
        )
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        """Update the state and attributes from coordinator data."""
        value: Any = self.coordinator.data["data"].get(self.entity_description.key)
        if isinstance(value, dict):
            self._attr_extra_state_attributes = dict(value)
            value = value.get("checkInAllowed")
        else:
            self._attr_extra_state_attributes = None
        self._attr_is_on = value if isinstance(value, bool) else bool(value)

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated booking data."""
        self._update_from_coordinator()
        super()._handle_coordinator_update()
