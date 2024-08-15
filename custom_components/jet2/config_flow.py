"""Config flow for Jet2 integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from .coordinator import Jet2Coordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from .const import DOMAIN, CONF_BOOKING_REFERENCE, CONF_DATE_OF_BIRTH, CONF_SURNAME, BOOKING_OPTION, ADD_BOOKING, REMOVE_BOOKING, CONF_ADD_BOOKING, CONF_REMOVE_BOOKING, CONF_BOOKING_REMOVED

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BOOKING_REFERENCE): cv.string,
        vol.Required(CONF_DATE_OF_BIRTH): cv.string,
        vol.Required(CONF_SURNAME): cv.string,
    }
)

STEP_BOOKING_OPTION_SCHEMA = vol.Schema(
    {
        vol.Required(BOOKING_OPTION, default=ADD_BOOKING): vol.In(
            (
                ADD_BOOKING,
                REMOVE_BOOKING,
            )
        )
    }
)

STEP_REMOVE_BOOKING_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BOOKING_REFERENCE): vol.In([]),
    }
)


@callback
def async_get_options_flow(config_entry):
    return Jet2FlowHandler(config_entry)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    session = async_get_clientsession(hass)

    coordinator = Jet2Coordinator(hass, session, data)

    await coordinator.async_refresh()

    if coordinator.last_exception is not None and data is not None:
        raise InvalidAuth

    return {"title": str(data[CONF_BOOKING_REFERENCE]).upper()}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jet2."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            if user_input[BOOKING_OPTION] == ADD_BOOKING:
                return await self.async_step_add_booking()
            elif user_input[BOOKING_OPTION] == REMOVE_BOOKING:
                return await self.async_step_remove_booking()

        return self.async_show_form(
            step_id="user", data_schema=STEP_BOOKING_OPTION_SCHEMA
        )

    async def async_step_import(self, import_data=None) -> FlowResult:
        """Handle the import step for the service call."""

        if import_data is not None:
            try:
                await self.async_set_unique_id(import_data[CONF_BOOKING_REFERENCE])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=import_data[CONF_BOOKING_REFERENCE], data=import_data
                )
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.error(f"Failed to import booking: {e}")
                return self.async_abort(reason="import_failed")

    async def async_step_add_booking(self, user_input=None) -> FlowResult:
        """Handle the add booking step."""
        if user_input is not None:
            errors = {}
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

            return self.async_show_form(
                step_id=CONF_ADD_BOOKING, data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        return self.async_show_form(
            step_id=CONF_ADD_BOOKING, data_schema=STEP_USER_DATA_SCHEMA
        )

    async def async_step_remove_booking(self, user_input=None) -> FlowResult:
        """Handle the remove booking step."""
        if user_input is not None:
            booking_reference = user_input[CONF_BOOKING_REFERENCE]

            await self.hass.services.async_call(
                DOMAIN,
                CONF_REMOVE_BOOKING,
                {
                    CONF_BOOKING_REFERENCE: booking_reference,
                },
                blocking=True
            )

            return self.async_abort(reason=CONF_BOOKING_REMOVED)

        # Fetch existing bookings for the dropdown
        entries = self._async_get_existing_bookings()
        return self.async_show_form(
            step_id=CONF_REMOVE_BOOKING,
            data_schema=STEP_REMOVE_BOOKING_SCHEMA.extend({
                vol.Required(CONF_BOOKING_REFERENCE): vol.In(entries),
            }),
            errors={}
        )

    def _async_get_existing_bookings(self) -> list[str]:
        """Get a list of existing booking references."""
        return [
            entry.data.get(CONF_BOOKING_REFERENCE)
            for entry in self.hass.config_entries.async_entries(DOMAIN)
        ]


class Jet2FlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
