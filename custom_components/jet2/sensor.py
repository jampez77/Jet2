"""Jet2 sensor platform."""

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_BOOKING_REFERENCE, DOMAIN
from .coordinator import Jet2Coordinator

SENSOR_TYPES = [
    SensorEntityDescription(
        key="departure", name="Departure", icon="mdi:airplane-takeoff"
    ),
    SensorEntityDescription(key="region", name="Region", icon="mdi:map"),
    SensorEntityDescription(key="area", name="Area", icon="mdi:map-outline"),
    SensorEntityDescription(key="resort", name="Resort", icon="mdi:beach"),
    SensorEntityDescription(
        key="numberOfPassengers",
        name="Number of Passengers",
        icon="mdi:account-multiple",
    ),
    SensorEntityDescription(
        key="reservedSeats", name="Reserved Seats", icon="mdi:seat-passenger"
    ),
    SensorEntityDescription(
        key="numberOfInclusiveBags",
        name="Number of Inclusive Bags",
        icon="mdi:bag-personal",
    ),
    SensorEntityDescription(
        key="numberOfAdditionalBags",
        name="Number of Additional Bags",
        icon="mdi:bag-personal-outline",
    ),
    SensorEntityDescription(
        key="insurance", name="Insurance", icon="mdi:shield-airplane"
    ),
    SensorEntityDescription(key="bookedMeals", name="Booked Meals", icon="mdi:food"),
    SensorEntityDescription(
        key="bookingReference", name="Booking Reference", icon="mdi:file-document"
    ),
    SensorEntityDescription(
        key="holidayType", name="Holiday Type", icon="mdi:information-outline"
    ),
    SensorEntityDescription(
        key="priceBreakdown", name="Price Breakdown", icon="mdi:cash"
    ),
    SensorEntityDescription(key="hotel", name="Hotel", icon="mdi:office-building"),
    SensorEntityDescription(
        key="flightSummary", name="Flight Summary", icon="mdi:airplane-settings"
    ),
    SensorEntityDescription(
        key="transferSummary", name="Transfer Summary", icon="mdi:bus"
    ),
    SensorEntityDescription(
        key="carHireSummaries", name="Car Hire Summary", icon="mdi:car-settings"
    ),
    SensorEntityDescription(
        key="numberOfFreeChildPlaces",
        name="Number of Free Child Places",
        icon="mdi:human-child",
    ),
    SensorEntityDescription(
        key="numberOfFreeInfantPlaces",
        name="Number of Free Infant Places",
        icon="mdi:baby",
    ),
    SensorEntityDescription(
        key="holidaySummaries", name="Holiday Summaries", icon="mdi:information-variant"
    ),
    SensorEntityDescription(
        key="holidayDuration",
        name="Holiday Duration",
        icon="mdi:calendar-start-outline",
    ),
    SensorEntityDescription(
        key="checkInStatus",
        name="Check-In Open",
        icon="mdi:airplane-check",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="checkInState",
        name="Check-In Status",
        icon="mdi:airplane-check",
    ),
    SensorEntityDescription(
        key="scheduleChangeInfo",
        name="Schedule Change Info",
        icon="mdi:information-variant-box",
    ),
    SensorEntityDescription(
        key="accommodationExtrasSummaries",
        name="Accommodation Extras Summaries",
        icon="mdi:information-box",
    ),
]


def hasBookingExpired(hass: HomeAssistant, expiry_date_raw: str) -> bool:
    """Check if booking has expired."""

    user_timezone = dt_util.get_time_zone(hass.config.time_zone)

    dt_utc = datetime.strptime(expiry_date_raw, "%Y-%m-%dT%H:%M:%S").replace(
        tzinfo=user_timezone
    )
    # Convert the datetime to the default timezone
    expiry_date = dt_utc.astimezone(user_timezone)

    return (expiry_date.timestamp() - datetime.today().timestamp()) <= 3600


async def removeBooking(hass: HomeAssistant, booking_reference: str):
    """Remove expired booking."""

    entry = next(
        (
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.data.get(CONF_BOOKING_REFERENCE) == booking_reference
        ),
        None,
    )

    # Remove the config entry
    await hass.config_entries.async_remove(entry.entry_id)


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

        success = bool(coordinator.data.get("success"))
        name = entry.data[CONF_BOOKING_REFERENCE]

        if success:
            if hasBookingExpired(hass, coordinator.data.get("data")["expiryDate"]):
                await removeBooking(hass, name)
            else:
                sensors = [
                    Jet2Sensor(coordinator, name, description)
                    for description in SENSOR_TYPES
                    if description.key in coordinator.data
                ]
                async_add_entities(sensors, update_before_add=True)
        else:
            await removeBooking(hass, name)


class Jet2Sensor(CoordinatorEntity[Jet2Coordinator], SensorEntity):
    """Define an Jet2 sensor."""

    def __init__(
        self,
        coordinator: Jet2Coordinator,
        name: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.success = bool(coordinator.data.get("success"))
        self.data = coordinator.data.get("data")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{name}")},
            manufacturer="Jet2",
            model=self.data.get("holidayType"),
            name=name.upper(),
            configuration_url="https://github.com/jampez77/Jet2/",
        )
        self._attr_unique_id = f"{DOMAIN}-{name}-{description.key}".lower()
        self.entity_id = f"sensor.{DOMAIN}_{name}_{description.key}".lower()
        self.attrs: dict[str, Any] = {}
        self.entity_description = description
        self.name = self.entity_description.name
        self._state = None

    def update_from_coordinator(self):
        """Update sensor state and attributes from coordinator data."""

        if not self.success:
            self.hass.async_add_job(removeBooking(self.hass, self.name))
        else:
            value = self.data.get(self.entity_description.key)

            if isinstance(value, (dict, list)):
                for index, attribute in enumerate(value):
                    if isinstance(attribute, (dict, list)):
                        for attr in attribute:
                            self.attrs[str(attr) + str(index)] = attribute[attr]
                    else:
                        self.attrs[attribute] = value[attribute]

            if self.entity_description.key == "checkInState":
                value = self.data.get("checkInStatus")
                if "checkInAllowed" in value:
                    if value["checkInAllowed"]:
                        _value = "Allowed"
                        if "outboundFlight" in value:
                            outboundFlight = value["outboundFlight"]
                            if (
                                outboundFlight is not None
                                and "checkedInCode" in outboundFlight
                            ):
                                _value = outboundFlight["checkedInCode"]
                        if "inboundFlight" in value:
                            inboundFlight = value["inboundFlight"]
                            if (
                                inboundFlight is not None
                                and "checkedInCode" in inboundFlight
                            ):
                                _value = inboundFlight["checkedInCode"]
                    else:
                        _value = "Not Allowed"
                value = _value

            if self.entity_description.key == "numberOfPassengers":
                passenger_count = 0
                for key in value:
                    passenger_count += value[key]
                value = passenger_count

            if isinstance(value, dict):
                if self.entity_description.key == "flightSummary":
                    value = value.get("outbound").get("number")
                else:
                    value = next(iter(value.values()))

            if isinstance(value, list):
                value = str(len(value))

            if (
                value
                and self.entity_description.device_class == SensorDeviceClass.TIMESTAMP
            ):
                user_timezone = dt_util.get_time_zone(self.hass.config.time_zone)

                dt_utc = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").replace(
                    tzinfo=user_timezone
                )
                # Convert the datetime to the default timezone
                value = dt_utc.astimezone(user_timezone)

            self._state = value

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
    def native_value(self) -> str | date | None:
        """Native value."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Define entity attributes."""
        return self.attrs
