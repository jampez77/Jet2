"""Jet2 sensor platform."""
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import DOMAIN, CONF_BOOKING_REFERENCE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .coordinator import Jet2Coordinator
from homeassistant.util import dt as dt_util
from homeassistant.components.sensor import (
    SensorEntityDescription,
)

DATE_SENSOR_TYPES = SENSOR_TYPES = [
    SensorEntityDescription(
        key="priceBreakdown",
        name="Payment Due",
    ),
    SensorEntityDescription(
        key="outbound",
        name="Outbound",
    ),
    SensorEntityDescription(
        key="inbound",
        name="Inbound",
    ),
    SensorEntityDescription(
        key="checkInStatus",
        name="Check-In Date",
    ),
    SensorEntityDescription(
        key="holiday",
        name="Holiday",
    ),
    SensorEntityDescription(
        key="expiryDate",
        name="Booking Expiration",
    )
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]
    # Update our config to include new repos and remove those that have been removed.
    if entry.options:
        config.update(entry.options)

    session = async_get_clientsession(hass)
    coordinator = Jet2Coordinator(hass, session, entry.data)

    await coordinator.async_refresh()

    name = entry.data[CONF_BOOKING_REFERENCE]

    sensors = [Jet2CalendarSensor(coordinator, name)]
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

    sensors = [Jet2CalendarSensor(coordinator, name)]
    async_add_entities(sensors, update_before_add=True)


class Jet2CalendarSensor(CoordinatorEntity[Jet2Coordinator], CalendarEntity):
    """Define an Jet2 sensor."""

    def __init__(
        self,
        coordinator: Jet2Coordinator,
        name: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.data = coordinator.data.get("data")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{name}")},
            manufacturer='Jet2 - ' + self.data.get("holidayType"),
            name=name,
            configuration_url="https://github.com/jampez77/Jet2/",
        )
        self._attr_unique_id = f"{DOMAIN}-{name}-calendar".lower()
        self._attr_name = f"{DOMAIN} - {name}".upper()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self.coordinator.data.get('success'))

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        events = self.get_events(datetime.today())
        return sorted(events, key=lambda c: c.start)[0]

    def get_events(self, start_date: datetime) -> list[CalendarEvent]:
        """Return calendar events."""
        events = []

        for date_sensor_type in DATE_SENSOR_TYPES:
            event_end_raw = None
            event_name = date_sensor_type.name

            if date_sensor_type.key == "priceBreakdown":

                if "paymentDateDue" in self.data.get(date_sensor_type.key):
                    event_start_raw = self.data.get(date_sensor_type.key)[
                        "paymentDateDue"]

            elif date_sensor_type.key == "checkInStatus":

                if "checkInDate" in self.data.get(date_sensor_type.key):
                    event_start_raw = self.data.get(date_sensor_type.key)[
                        "checkInDate"]

            elif date_sensor_type.key == "holiday":

                if "flightSummary" in self.data:
                    flightSummary = self.data.get("flightSummary")

                    if "outbound" in flightSummary:
                        outbound = flightSummary["outbound"]

                        if "localDepartureDateTime" in outbound:
                            event_start_raw = outbound["localDepartureDateTime"]

                    if "inbound" in flightSummary:
                        inbound = flightSummary["inbound"]

                        if "localArrivalDateTime" in inbound:
                            event_end_raw = inbound["localArrivalDateTime"]

                if "hotel" in self.data:
                    event_name = self.data["hotel"]["name"]
                elif "resort" in self.data:
                    event_name = self.data["resort"]
                elif "area" in self.data:
                    event_name = self.data["area"]
                elif "region" in self.data:
                    event_name = self.data["region"]

            elif date_sensor_type.key == "outbound" or date_sensor_type.key == "inbound":

                if "flightSummary" in self.data:
                    flightSummary = self.data.get("flightSummary")

                    if date_sensor_type.key in flightSummary:
                        bound = flightSummary[date_sensor_type.key]

                        if "localDepartureDateTime" in bound:
                            event_start_raw = bound["localDepartureDateTime"]

                        if "localArrivalDateTime" in bound:
                            event_end_raw = bound["localArrivalDateTime"]

                        if "departureAirport" in bound and "arrivalAirport" in bound:
                            departureAirport = bound["departureAirport"]
                            arrivalAirport = bound["arrivalAirport"]

                            if "displayName" in departureAirport and "displayName" in arrivalAirport:
                                event_name = departureAirport["displayName"] + \
                                    " - " + arrivalAirport["displayName"]
            else:
                event_start_raw = self.data.get(date_sensor_type.key)

            if not event_start_raw:
                continue

            user_timezone = dt_util.get_time_zone(
                self.hass.config.time_zone)

            start_dt_utc = datetime.strptime(
                event_start_raw, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=user_timezone)
            # Convert the datetime to the default timezone
            event_start = start_dt_utc.astimezone(user_timezone)

            if event_end_raw is None:
                event_end_raw = event_start_raw

            end_dt_utc = datetime.strptime(
                event_end_raw, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=user_timezone)
            # Convert the datetime to the default timezone
            event_end = end_dt_utc.astimezone(user_timezone)
            if event_start.date() >= start_date.date():
                events.append(CalendarEvent(
                    event_start, event_end, event_name))
        return events

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events = []
        for event in self.get_events(start_date):
            if event.start.date() <= end_date.date():
                events.append(event)
        return events
