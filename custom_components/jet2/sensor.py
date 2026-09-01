"""Sensor platform for the Jet2 integration."""

from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_BOOKING_REFERENCE, DOMAIN
from .coordinator import Jet2ConfigEntry, Jet2Coordinator

SENSOR_TYPES = (
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
        key="holidaySummaries",
        name="Holiday Summaries",
        icon="mdi:information-variant",
    ),
    SensorEntityDescription(
        key="holidayDuration",
        name="Holiday Duration",
        icon="mdi:calendar-start-outline",
    ),
    SensorEntityDescription(
        key="checkInStatus",
        name="Check-In Date",
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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Jet2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Jet2 sensors."""
    coordinator = entry.runtime_data
    booking = coordinator.data["data"]
    async_add_entities(
        Jet2Sensor(coordinator, entry.data[CONF_BOOKING_REFERENCE], description)
        for description in SENSOR_TYPES
        if description.key in booking or description.key == "checkInState"
    )


class Jet2Sensor(CoordinatorEntity[Jet2Coordinator], SensorEntity):
    """Represent a value from a Jet2 booking."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Jet2Coordinator,
        booking_reference: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}-{booking_reference}-{description.key}".lower()
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
        booking = self.coordinator.data["data"]
        key = self.entity_description.key
        raw_value = booking.get(key)

        if key == "checkInState":
            raw_value = booking.get("checkInStatus")

        if isinstance(raw_value, dict):
            self._attr_extra_state_attributes = dict(raw_value)
        elif isinstance(raw_value, list) and raw_value:
            self._attr_extra_state_attributes = {"items": raw_value}
        else:
            self._attr_extra_state_attributes = None

        value: Any = raw_value
        if key == "checkInState":
            value = self._check_in_state(raw_value)
        elif key == "numberOfPassengers" and isinstance(raw_value, dict):
            value = sum(
                passenger_count
                for passenger_count in raw_value.values()
                if isinstance(passenger_count, int)
            )
        elif key == "checkInStatus" and isinstance(raw_value, dict):
            value = raw_value.get("checkInDate")
        elif key == "priceBreakdown" and isinstance(raw_value, dict):
            value = raw_value.get("total")
        elif key == "hotel" and isinstance(raw_value, dict):
            value = raw_value.get("name")
        elif key == "flightSummary" and isinstance(raw_value, dict):
            outbound = raw_value.get("outbound")
            value = outbound.get("number") if isinstance(outbound, dict) else None
        elif isinstance(raw_value, dict):
            value = next(
                (
                    item
                    for item in raw_value.values()
                    if isinstance(item, (bool, float, int, str))
                ),
                None,
            )
        elif isinstance(raw_value, list):
            value = len(raw_value)

        if (
            isinstance(value, str)
            and self.entity_description.device_class == SensorDeviceClass.TIMESTAMP
        ):
            parsed = dt_util.parse_datetime(value)
            if parsed is not None and parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=dt_util.get_time_zone(self.coordinator.hass.config.time_zone)
                )
            value = parsed

        self._attr_native_value = value

    @staticmethod
    def _check_in_state(value: Any) -> str | None:
        """Return a readable check-in state."""
        if not isinstance(value, dict):
            return None
        if not value.get("checkInAllowed"):
            return "Not Allowed"

        for flight_key in ("outboundFlight", "inboundFlight"):
            flight = value.get(flight_key)
            if isinstance(flight, dict) and flight.get("checkedInCode"):
                return str(flight["checkedInCode"])
        return "Allowed"

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated booking data."""
        self._update_from_coordinator()
        super()._handle_coordinator_update()
