"""Jet2 sensor platform."""

from datetime import datetime, timedelta
import hashlib
import json
import uuid

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_BOOKING_REFERENCE, CONF_CALENDARS, DOMAIN
from .coordinator import Jet2Coordinator

DATE_SENSOR_TYPES = [
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
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""

    config = hass.data[DOMAIN][entry.entry_id]
    # Update our config to include new repos and remove those that have been removed.
    if entry.options:
        config.update(entry.options)

    session = async_get_clientsession(hass)
    coordinator = Jet2Coordinator(hass, session, entry.data)

    await coordinator.async_refresh()

    success = bool(coordinator.data.get("success"))

    if success:
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


async def create_event(hass: HomeAssistant, service_data):
    """Create calendar event."""
    try:
        await hass.services.async_call(
            "calendar",
            "create_event",
            service_data,
            blocking=True,
            return_response=True,
        )
    except (ServiceValidationError, HomeAssistantError):
        await hass.services.async_call(
            "calendar",
            "create_event",
            service_data,
            blocking=True,
        )


class DateTimeEncoder(json.JSONEncoder):
    """Encode date time object."""

    def default(self, o):
        """Encode date time object."""
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def generate_uuid_from_json(json_obj):
    """Generate a UUID from a JSON object."""

    json_string = json.dumps(json_obj, cls=DateTimeEncoder, sort_keys=True)

    sha1_hash = hashlib.sha1(json_string.encode("utf-8")).digest()

    return str(uuid.UUID(bytes=sha1_hash[:16]))


async def get_event_uid(hass: HomeAssistant, service_data) -> str | None:
    """Fetch the created event by matching with details in service_data."""
    entity_id = service_data.get("entity_id")
    start_time = service_data.get("start_date_time")
    end_time = service_data.get("end_date_time")

    try:
        events = await hass.services.async_call(
            "calendar",
            "get_events",
            {
                "entity_id": entity_id,
                "start_date_time": start_time,
                "end_date_time": end_time,
            },
            return_response=True,
            blocking=True,
        )
    except (ServiceValidationError, HomeAssistantError):
        events = None

    if events is not None and entity_id in events:
        for event in events[entity_id].get("events"):
            if (
                event["summary"] == service_data["summary"]
                and f"{event["description"]}" == f"{service_data["description"]}"
                and f"{event["location"]}" == f"{service_data["location"]}"
            ):
                return generate_uuid_from_json(service_data)

    return None


async def add_to_calendar(
    hass: HomeAssistant, calendar: str, event: CalendarEvent, entry: ConfigEntry
):
    """Add an event to the calendar."""

    service_data = {
        "entity_id": calendar,
        "start_date_time": event.start,
        "end_date_time": event.end,
        "summary": event.summary,
        "description": f"{event.description}",
        "location": f"{event.location}",
    }

    uid = await get_event_uid(hass, service_data)

    uids = entry.data.get("uids", [])

    if uid not in uids:
        await create_event(hass, service_data)

        created_event_uid = await get_event_uid(hass, service_data)

        if created_event_uid is not None and created_event_uid not in uids:
            uids.append(created_event_uid)

    if uids != entry.data.get("uids", []):
        updated_data = entry.data.copy()
        updated_data["uids"] = uids
        hass.config_entries.async_update_entry(entry, data=updated_data)


class Jet2CalendarSensor(CoordinatorEntity[Jet2Coordinator], CalendarEntity):
    """Define an Jet2 sensor."""

    def __init__(
        self,
        coordinator: Jet2Coordinator,
        name: str,
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
            self._attr_unique_id = f"{DOMAIN}-{name}-calendar".lower()
            self._attr_name = f"{DOMAIN.title()} - {name.upper()}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.success

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if self.success:
            events = self.get_events(datetime.today(), self.hass)
            return sorted(events, key=lambda c: c.start)[0]
        return None

    def get_events(
        self, start_date: datetime, hass: HomeAssistant
    ) -> list[CalendarEvent]:
        """Return calendar events."""
        events = []

        for date_sensor_type in DATE_SENSOR_TYPES:
            event_end_raw = None
            event_name = date_sensor_type.name
            event_location = event_name
            event_description = f"Jet2|{self.data["bookingReference"]}"

            if (
                date_sensor_type.key == "priceBreakdown"
                and "paymentDateDue" in self.data.get(date_sensor_type.key)
            ):
                event_start_raw = self.data.get(date_sensor_type.key)["paymentDateDue"]

            elif (
                date_sensor_type.key == "checkInStatus"
                and "checkInDate" in self.data.get(date_sensor_type.key)
            ):
                event_start_raw = self.data.get(date_sensor_type.key)["checkInDate"]

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

                event_location = event_name
                if (
                    "hotel" in self.data
                    and "resort" in self.data
                    and "area" in self.data
                    and "region" in self.data
                ):
                    event_location = (
                        self.data["hotel"]["name"]
                        + ", "
                        + self.data["resort"]
                        + ", "
                        + self.data["area"]
                        + ", "
                        + self.data["region"]
                    )
            else:
                event_start_raw = self.data.get(date_sensor_type.key)

            if not event_start_raw:
                continue

            user_timezone = dt_util.get_time_zone(hass.config.time_zone)

            start_dt_utc = datetime.strptime(
                event_start_raw, "%Y-%m-%dT%H:%M:%S"
            ).replace(tzinfo=user_timezone)
            # Convert the datetime to the default timezone
            event_start = start_dt_utc.astimezone(user_timezone)

            if event_end_raw is None:
                event_end_raw = event_start_raw

            end_dt_utc = datetime.strptime(event_end_raw, "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=user_timezone
            )

            # Convert the datetime to the default timezone
            event_end = end_dt_utc.astimezone(user_timezone)

            event_end += timedelta(seconds=1)

            if event_start.date() >= start_date.date():
                events.append(
                    CalendarEvent(
                        event_start,
                        event_end,
                        event_name,
                        event_description,
                        event_location,
                    )
                )

        return events

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return [
            event
            for event in self.get_events(start_date, hass)
            if event.start.date() <= end_date.date()
        ]
