"""The Jet2 integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import Jet2ConfigEntry, Jet2Coordinator
from .services import async_setup_services

PLATFORMS = (
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.CAMERA,
    Platform.SENSOR,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Jet2 integration."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: Jet2ConfigEntry) -> bool:
    """Set up Jet2 from a config entry."""
    coordinator = Jet2Coordinator(hass, entry, async_get_clientsession(hass))
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Jet2ConfigEntry) -> bool:
    """Unload a Jet2 config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
