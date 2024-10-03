"""Jet2 binary sensor platform."""

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BOOKING_REFERENCE, DOMAIN
from .coordinator import Jet2Coordinator

SENSOR_TYPES = [
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
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]

    if entry.options:
        config.update(entry.options)

    if entry.data:
        session = async_get_clientsession(hass)

        coordinator = Jet2Coordinator(hass, session, entry.data)

        await coordinator.async_refresh()

        name = entry.data[CONF_BOOKING_REFERENCE]

        sensors = [
            Jet2BinarySensor(coordinator, name, description)
            for description in SENSOR_TYPES
            if description.key in coordinator.data
        ]
        async_add_entities(sensors, update_before_add=True)


class Jet2BinarySensor(CoordinatorEntity[Jet2Coordinator], BinarySensorEntity):
    """Define an Jet2 sensor."""

    def __init__(
        self,
        coordinator: Jet2Coordinator,
        name: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.success = bool(coordinator.data.get("success"))

        if self.success:
            self.data = coordinator.data.get("data")
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{name}")},
                manufacturer="Jet2",
                model=self.data.get("holidayType"),
                name=name.upper(),
                configuration_url="https://github.com/jampez77/Jet2/",
            )
            self._attr_unique_id = f"{DOMAIN}-{name}-{description.key}-binary".lower()
            self.entity_id = f"binary_sensor.{DOMAIN}_{name}_{description.key}".lower()
            self.attrs: dict[str, Any] = {}
            self.entity_description = description
            self._attr_is_on = None

    def update_from_coordinator(self):
        """Update sensor state and attributes from coordinator data."""
        if self.success:
            value: dict | str | bool = self.data.get(self.entity_description.key, None)

            if (
                isinstance(value, dict)
                and self.entity_description.key == "checkInStatus"
            ):
                value = value["checkInAllowed"]

            self._attr_is_on = bool(value)

            if isinstance(value, (dict, list)):
                for index, attribute in enumerate(value):
                    if isinstance(attribute, (dict, list)):
                        for attr in attribute:
                            self.attrs[str(attr) + str(index)] = attribute[attr]
                    else:
                        self.attrs[attribute] = value[attribute]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_from_coordinator()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle adding to Home Assistant."""
        await super().async_added_to_hass()
        await self.async_update()

    async def async_remove(self) -> None:
        """Handle the removal of the entity."""
        # If you have any specific cleanup logic, add it here
        if self.hass is not None:
            await super().async_remove()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.success

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._attr_is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Define entity attributes."""
        return self.attrs
