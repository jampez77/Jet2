from homeassistant.core import HomeAssistant, ServiceCall
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from .const import (
    DOMAIN,
    CONF_BOOKING_REFERENCE,
    CONF_DATE_OF_BIRTH,
    CONF_SURNAME,
    CONF_ADD_BOOKING,
    CONF_REMOVE_BOOKING,
    CONF_CREATE_CALENDAR,
    CONF_CALENDARS,
)
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from .coordinator import Jet2Coordinator
import functools


# Define the schema for your service
SERVICE_ADD_BOOKING_SCHEMA = vol.Schema(
    {
        **cv.ENTITY_SERVICE_FIELDS,
        vol.Required(CONF_CREATE_CALENDAR): cv.boolean,
        vol.Required(CONF_BOOKING_REFERENCE): cv.string,
        vol.Required(CONF_DATE_OF_BIRTH): cv.string,
        vol.Required(CONF_SURNAME): cv.string,
    }
)

SERVICE_REMOVE_BOOKING_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BOOKING_REFERENCE): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jet2 from a config entry."""

    # Create a coordinator or other necessary components
    session = async_get_clientsession(hass)
    coordinator = Jet2Coordinator(hass, session, entry.data)

    # Store the coordinator so it can be accessed by other parts of the integration
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup the service (if it hasn't already been set up globally)
    async_setup_services(hass)

    # You may also register entities, update the coordinator, etc.
    await coordinator.async_refresh()

    if coordinator.last_exception is not None:
        return False

    return True


def async_cleanup_services(hass: HomeAssistant) -> None:
    """Cleanup Jet2 services."""
    hass.services.async_remove(DOMAIN, CONF_ADD_BOOKING)
    hass.services.async_remove(DOMAIN, CONF_REMOVE_BOOKING)


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Jet2 services."""
    services = [
        (
            CONF_ADD_BOOKING,
            functools.partial(add_booking, hass),
            SERVICE_ADD_BOOKING_SCHEMA,
        ),
        (
            CONF_REMOVE_BOOKING,
            functools.partial(remove_booking, hass),
            SERVICE_REMOVE_BOOKING_SCHEMA,
        ),
    ]
    for name, method, schema in services:
        if hass.services.has_service(DOMAIN, name):
            continue
        hass.services.async_register(DOMAIN, name, method, schema=schema)


async def add_booking(hass: HomeAssistant, call: ServiceCall) -> None:
    """Add a booking."""
    booking_reference = call.data.get(CONF_BOOKING_REFERENCE)
    date_of_birth = call.data.get(CONF_DATE_OF_BIRTH)
    surname = call.data.get(CONF_SURNAME)
    create_calendar = call.data.get(CONF_CREATE_CALENDAR)
    calendars = call.data.get(CONF_ENTITY_ID)

    calendar_entities = {}

    if create_calendar:
        calendar_entities["None"] = "Create a new calendar"

    for calendar in calendars:
        calendar_entity = hass.states.get(calendar)
        if calendar_entity:
            calendar_entities[calendar] = calendar

    entries = hass.config_entries.async_entries(DOMAIN)
    if any(
        entry.data.get(CONF_BOOKING_REFERENCE) == booking_reference for entry in entries
    ):
        return

    # Initiate the config flow with the "import" step
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "import"},
        data={
            CONF_BOOKING_REFERENCE: booking_reference,
            CONF_DATE_OF_BIRTH: date_of_birth,
            CONF_SURNAME: surname,
            CONF_CALENDARS: calendar_entities,
        },
    )

    # Notify user
    hass.components.persistent_notification.create(
        f"Added Jet2 booking {booking_reference}", title="Jet2 Booking Added"
    )


async def remove_booking(hass: HomeAssistant, call: ServiceCall) -> None:
    """Remove a booking, its device, and all related entities."""
    booking_reference = call.data.get(CONF_BOOKING_REFERENCE)

    # Find the config entry corresponding to the booking reference
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
