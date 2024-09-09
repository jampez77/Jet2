"""Jet2 sensor platform."""
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import (
    DOMAIN,
    CONF_BOOKING_REFERENCE,
    CONF_CALENDARS
)
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
import uuid
import hashlib
import json
from .coordinator import Jet2Coordinator
from homeassistant.util import dt as dt_util
from homeassistant.components.sensor import (
    SensorEntityDescription,
)
from datetime import timedelta

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

    calendars = entry.data[CONF_CALENDARS]

    sensors = [Jet2CalendarSensor(coordinator, name)]

    for calendar in calendars:
        if calendar != "None":
            for sensor in sensors:
                events = sensor.get_events(datetime.today(), hass)
                for event in events:
                    await add_to_calendar(hass, calendar, event, entry)

    if "None" in calendars:
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

    calendars = config[CONF_CALENDARS]

    sensors = [Jet2CalendarSensor(coordinator, name)]

    for calendar in calendars:
        if calendar != "None":
            for sensor in sensors:
                events = sensor.get_events(datetime.today(), hass)
                for event in events:
                    await add_to_calendar(hass, calendar, event, config)

    if "None" in calendars:
        async_add_entities(sensors, update_before_add=True)


async def create_event(hass: HomeAssistant, service_data):
    await hass.services.async_call(
        "calendar",
        "create_event",
        service_data,
        blocking=True,
    )


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def generate_uuid_from_json(json_obj):
    """Generate a UUID from a JSON object."""

    json_string = json.dumps(json_obj, cls=DateTimeEncoder, sort_keys=True)

    sha1_hash = hashlib.sha1(json_string.encode('utf-8')).digest()

    return str(uuid.UUID(bytes=sha1_hash[:16]))


async def get_event_uid(hass: HomeAssistant, service_data) -> str | None:
    """ Fetch the created event by matching with details in service_data """
    entity_id = service_data.get("entity_id")
    start_time = service_data.get("start_date_time")
    end_time = service_data.get("end_date_time")

    try:
        events = await hass.services.async_call(
            "calendar",
            "list_events",
            {
                "entity_id": entity_id,
                "start_date_time": start_time,
                "end_date_time": end_time,
            },
            return_response=True,
            blocking=True,
        )
    except:
        events = await hass.services.async_call(
            "calendar",
            "list_events",
            {
                "entity_id": entity_id,
                "start_date_time": start_time,
                "end_date_time": end_time,
            },
            blocking=True,
        )

    if events is not None:
        for event in events.get("events"):
            if event["summary"] == service_data["summary"] and event["description"] == service_data["description"] and event["location"] == service_data["location"]:
                return generate_uuid_from_json(service_data)

    return None


async def add_to_calendar(hass: HomeAssistant, calendar: str, event: CalendarEvent, entry: ConfigEntry):
    """Add an event to the calendar."""

    service_data = {
        "entity_id": calendar,
        "start_date_time": event.start,
        "end_date_time": event.end,
        "summary": event.summary,
        "description": f"{event.description}",
        "location": f"{event.location}"
    }

    uid = await get_event_uid(hass, service_data)

    if "uids" not in entry.data:
        uids = []
    else:
        uids = entry.data["uids"]

    if uid not in uids:

        await create_event(hass, service_data)

        created_event_uid = await get_event_uid(hass, service_data)

        if created_event_uid not in uids:
            uids.append(created_event_uid)

        updated_data = entry.data.copy()
        updated_data["uids"] = uids
        hass.config_entries.async_update_entry(
            entry, data=updated_data)


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
            name=name.upper(),
            configuration_url="https://github.com/jampez77/Jet2/",
        )
        self._attr_unique_id = f"{DOMAIN}-{name}-calendar".lower()
        self._attr_name = f"{DOMAIN.title()} - {name.upper()}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self.coordinator.data.get('success'))

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        events = self.get_events(datetime.today(), self.hass)
        return sorted(events, key=lambda c: c.start)[0]

    def get_events(self, start_date: datetime, hass: HomeAssistant) -> list[CalendarEvent]:
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

            user_timezone = dt_util.get_time_zone(hass.config.time_zone)

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

            event_end += timedelta(seconds=1)

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
        for event in self.get_events(start_date, hass):
            if event.start.date() <= end_date.date():
                events.append(event)
        return events
