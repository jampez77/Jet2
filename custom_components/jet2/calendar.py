"""Calendar platform for the Jet2 integration."""

from datetime import datetime, timedelta
import hashlib
import json
from typing import Any, override
import uuid

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_BOOKING_REFERENCE, CONF_CALENDARS, DOMAIN
from .coordinator import Jet2ConfigEntry, Jet2Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Jet2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Jet2 itinerary calendar."""
    calendar = Jet2Calendar(entry.runtime_data, entry.data[CONF_BOOKING_REFERENCE])
    selected_calendars = entry.data[CONF_CALENDARS]

    for entity_id in selected_calendars:
        if entity_id == "None":
            continue
        for event in calendar.events_between(
            dt_util.now(), dt_util.now() + timedelta(days=730), hass
        ):
            await add_to_calendar(hass, entity_id, event, entry)

    if "None" in selected_calendars:
        async_add_entities([calendar])


async def create_event(hass: HomeAssistant, service_data: dict[str, Any]) -> None:
    """Create a calendar event."""
    try:
        await hass.services.async_call(
            "calendar",
            "create_event",
            service_data,
            blocking=True,
            return_response=True,
        )
    except ServiceValidationError, HomeAssistantError:
        await hass.services.async_call(
            "calendar",
            "create_event",
            service_data,
            blocking=True,
        )


class DateTimeEncoder(json.JSONEncoder):
    """Encode datetimes for stable event identifiers."""

    @override
    def default(self, o: Any) -> Any:
        """Encode a datetime as ISO 8601."""
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def generate_uuid_from_json(json_obj: dict[str, Any]) -> str:
    """Generate a stable UUID from calendar service data."""
    json_string = json.dumps(json_obj, cls=DateTimeEncoder, sort_keys=True)
    sha1_hash = hashlib.sha1(json_string.encode()).digest()
    return str(uuid.UUID(bytes=sha1_hash[:16]))


async def get_event_uid(
    hass: HomeAssistant, service_data: dict[str, Any]
) -> str | None:
    """Return an identifier if the event already exists."""
    entity_id = service_data["entity_id"]
    try:
        events = await hass.services.async_call(
            "calendar",
            "get_events",
            {
                "entity_id": entity_id,
                "start_date_time": service_data["start_date_time"],
                "end_date_time": service_data["end_date_time"],
            },
            return_response=True,
            blocking=True,
        )
    except ServiceValidationError, HomeAssistantError:
        return None

    if not isinstance(events, dict) or entity_id not in events:
        return None

    for event in events[entity_id].get("events", []):
        if (
            event.get("summary") == service_data["summary"]
            and str(event.get("description")) == service_data["description"]
            and str(event.get("location")) == service_data["location"]
        ):
            return generate_uuid_from_json(service_data)
    return None


async def add_to_calendar(
    hass: HomeAssistant,
    calendar: str,
    event: CalendarEvent,
    entry: Jet2ConfigEntry,
) -> None:
    """Copy a Jet2 event to another calendar without duplicating it."""
    service_data = {
        "entity_id": calendar,
        "start_date_time": event.start,
        "end_date_time": event.end,
        "summary": event.summary,
        "description": str(event.description),
        "location": str(event.location),
    }
    uid = await get_event_uid(hass, service_data)
    uids = list(entry.data.get("uids", []))

    if uid not in uids:
        await create_event(hass, service_data)
        created_event_uid = await get_event_uid(hass, service_data)
        if created_event_uid is not None and created_event_uid not in uids:
            uids.append(created_event_uid)

    if uids != entry.data.get("uids", []):
        hass.config_entries.async_update_entry(entry, data={**entry.data, "uids": uids})


class Jet2Calendar(CoordinatorEntity[Jet2Coordinator], CalendarEntity):
    """Represent a Jet2 itinerary as a calendar."""

    _attr_has_entity_name = True
    _attr_name = "Itinerary"

    def __init__(self, coordinator: Jet2Coordinator, booking_reference: str) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}-{booking_reference}-calendar".lower()
        booking = coordinator.data["data"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, booking_reference)},
            manufacturer="Jet2",
            model=booking.get("holidayType"),
            name=booking_reference.upper(),
            configuration_url="https://github.com/jampez77/Jet2/",
        )

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        return min(
            (
                event
                for event in self._booking_events(self.hass)
                if isinstance(event.end, datetime) and event.end >= now
            ),
            key=lambda event: event.start,
            default=None,
        )

    def events_between(
        self,
        start_date: datetime,
        end_date: datetime,
        hass: HomeAssistant,
    ) -> list[CalendarEvent]:
        """Return booking events that overlap a time range."""
        return [
            event
            for event in self._booking_events(hass)
            if isinstance(event.start, datetime)
            and isinstance(event.end, datetime)
            and event.end >= start_date
            and event.start <= end_date
        ]

    @override
    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return self.events_between(start_date, end_date, hass)

    def _booking_events(self, hass: HomeAssistant) -> list[CalendarEvent]:
        """Build calendar events from the current booking data."""
        booking = self.coordinator.data["data"]
        booking_reference = str(booking["bookingReference"])
        description = f"Jet2|{booking_reference}"
        events: list[CalendarEvent] = []

        price_breakdown = booking.get("priceBreakdown")
        if isinstance(price_breakdown, dict):
            self._append_event(
                events,
                hass,
                "Payment Due",
                price_breakdown.get("paymentDateDue"),
                description=description,
            )

        check_in_status = booking.get("checkInStatus")
        if isinstance(check_in_status, dict):
            self._append_event(
                events,
                hass,
                "Check-In Date",
                check_in_status.get("checkInDate"),
                description=description,
            )

        flight_summary = booking.get("flightSummary")
        outbound: dict[str, Any] | None = None
        inbound: dict[str, Any] | None = None
        if isinstance(flight_summary, dict):
            if isinstance(flight_summary.get("outbound"), dict):
                outbound = flight_summary["outbound"]
                self._append_event(
                    events,
                    hass,
                    self._flight_summary("Outbound", outbound),
                    outbound.get("localDepartureDateTime"),
                    outbound.get("localArrivalDateTime"),
                    description,
                    str(booking.get("departure", "")),
                )
            if isinstance(flight_summary.get("inbound"), dict):
                inbound = flight_summary["inbound"]
                self._append_event(
                    events,
                    hass,
                    self._flight_summary("Inbound", inbound),
                    inbound.get("localDepartureDateTime"),
                    inbound.get("localArrivalDateTime"),
                    description,
                    str(booking.get("resort", "")),
                )

        if outbound is not None and inbound is not None:
            hotel = booking.get("hotel")
            holiday_name = (
                str(hotel.get("name"))
                if isinstance(hotel, dict) and hotel.get("name")
                else str(booking.get("resort", "Holiday"))
            )
            location_parts = [
                holiday_name,
                booking.get("resort"),
                booking.get("area"),
                booking.get("region"),
            ]
            self._append_event(
                events,
                hass,
                holiday_name,
                outbound.get("localDepartureDateTime"),
                inbound.get("localArrivalDateTime"),
                description,
                ", ".join(
                    str(part)
                    for part in location_parts
                    if isinstance(part, str) and part
                ),
            )

        return events

    @staticmethod
    def _flight_summary(direction: str, flight: dict[str, Any]) -> str:
        """Return a flight event summary."""
        number = flight.get("number")
        return f"{direction} flight {number}" if number else f"{direction} flight"

    @staticmethod
    def _append_event(
        events: list[CalendarEvent],
        hass: HomeAssistant,
        summary: str,
        start_raw: Any,
        end_raw: Any = None,
        description: str | None = None,
        location: str | None = None,
    ) -> None:
        """Append an event when its Jet2 date values are valid."""
        start = _parse_local_datetime(start_raw, hass)
        if start is None:
            return

        end = _parse_local_datetime(end_raw, hass)
        if end is None or end <= start:
            end = start + timedelta(minutes=1)
        events.append(
            CalendarEvent(
                start=start,
                end=end,
                summary=summary,
                description=description,
                location=location,
            )
        )


def _parse_local_datetime(value: Any, hass: HomeAssistant) -> datetime | None:
    """Parse a Jet2 local datetime using Home Assistant's timezone."""
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.get_time_zone(hass.config.time_zone))
    return parsed
