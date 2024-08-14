
from homeassistant.core import HomeAssistant, ServiceCall
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, CONF_BOOKING_REFERENCE, CONF_DATE_OF_BIRTH, CONF_SURNAME
from homeassistant.config_entries import ConfigEntryState, ConfigEntry
import functools

SERVICE_ADD_BOOKING = "add_booking"

# Define the schema for your service
SERVICE_ADD_BOOKING_SCHEMA = vol.Schema({
    vol.Required(CONF_BOOKING_REFERENCE): cv.string,
    vol.Required(CONF_DATE_OF_BIRTH): cv.string,
    vol.Required(CONF_SURNAME): cv.string,
})


def async_cleanup_services(hass: HomeAssistant) -> None:
    """Cleanup global UniFi Protect services (if all config entries unloaded)."""
    hass.services.async_remove(DOMAIN, SERVICE_ADD_BOOKING)


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the global UniFi Protect services."""
    services = [
        (
            SERVICE_ADD_BOOKING,
            functools.partial(add_booking, hass),
            SERVICE_ADD_BOOKING_SCHEMA,
        )
    ]
    for name, method, schema in services:
        if hass.services.has_service(DOMAIN, name):
            continue
        hass.services.async_register(DOMAIN, name, method, schema=schema)


async def add_booking(hass: HomeAssistant, call: ServiceCall) -> None:
    booking_reference = call.data.get(CONF_BOOKING_REFERENCE)
    date_of_birth = call.data.get(CONF_DATE_OF_BIRTH)
    surname = call.data.get(CONF_SURNAME)

    entry_id = f"{booking_reference}_{date_of_birth}_{surname}"
    config_entry = {
        'entry_id': entry_id,
        'version': 1,
        'domain': DOMAIN,
        'title': booking_reference,
        'data': {
            CONF_BOOKING_REFERENCE: booking_reference,
            CONF_DATE_OF_BIRTH: date_of_birth,
            CONF_SURNAME: surname,
        },
        'options': {},
        'source': 'service',
    }
    print(config_entry)
    # Check if an entry with the same ID already exists
    if any(entry.entry_id == entry_id for entry in hass.config_entries.async_entries(DOMAIN)):
        hass.components.persistent_notification.create(
            f"Booking {booking_reference} already exists.",
            title="Jet2 Booking Exists"
        )
        return

    # Add the configuration entry
    await hass.config_entries.async_add(config_entry)

    # Notify user or log
    hass.components.persistent_notification.create(
        f"Added Jet2 booking {booking_reference}",
        title="Jet2 Booking Added"
    )
