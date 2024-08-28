"""Jet2 binary sensor platform."""
from homeassistant.core import HomeAssistant
from typing import Any
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import DOMAIN, CONF_BOOKING_REFERENCE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
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
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]

    if entry.options:
        config.update(entry.options)

    if entry.data:

        session = async_get_clientsession(hass)

        coordinator = Jet2Coordinator(hass, session, entry.data)

        await coordinator.async_refresh()

        name = entry.data[CONF_BOOKING_REFERENCE]

        sensors = [Jet2BinarySensor(coordinator, name, description)
                   for description in SENSOR_TYPES]
        async_add_entities(sensors, update_before_add=True)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    _: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)

    coordinator = Jet2Coordinator(hass, session, config)

    name = config[CONF_BOOKING_REFERENCE]

    sensors = [Jet2BinarySensor(coordinator, name, description)
               for description in SENSOR_TYPES]
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
        self.data = coordinator.data.get('data')
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{name}")},
            manufacturer='Jet2 - ' + self.data.get("holidayType"),
            name=name.upper(),
            configuration_url="https://github.com/jampez77/Jet2/",
        )
        self._attr_unique_id = f"{DOMAIN}-{name}-{description.key}-binary".lower()
        self.entity_id = f"binary_sensor.{DOMAIN}_{name}_{description.key}".lower(
        )
        self.attrs: dict[str, Any] = {}
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self.coordinator.data.get('success'))

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""

        value: dict | str | bool = self.data.get(
            self.entity_description.key, None)

        if isinstance(value, dict) and self.entity_description.key == "checkInStatus":
            value = value["checkInAllowed"]

        return bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:

        value = self.data.get(self.entity_description.key)
        if isinstance(value, dict) or isinstance(value, list):
            for index, attribute in enumerate(value):
                if isinstance(attribute, list) or isinstance(attribute, dict):
                    for attr in attribute:
                        self.attrs[str(attr) + str(index)
                                   ] = attribute[attr]
                else:
                    self.attrs[attribute] = value[attribute]

        return self.attrs
