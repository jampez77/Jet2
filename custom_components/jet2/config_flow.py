"""Config flow for Jet2 integration."""
from __future__ import annotations

import logging
from typing import Any

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
from .const import DOMAIN, CONF_BOOKING_REFERENCE, CONF_DATE_OF_BIRTH, CONF_SURNAME, BOOKING_OPTION, ADD_BOOKING, REMOVE_BOOKING, CONF_ADD_BOOKING, CONF_REMOVE_BOOKING

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


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    session = async_get_clientsession(hass)

    coordinator = Jet2Coordinator(hass, session, data)

    await coordinator.async_refresh()

    if coordinator.last_exception is not None and data is not None:
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": str(data[CONF_BOOKING_REFERENCE]).upper()}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jet2."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Based on the user's choice, direct them to the appropriate step
            if user_input[BOOKING_OPTION] == ADD_BOOKING:
                return await self.async_step_add_booking()
            elif user_input[BOOKING_OPTION] == REMOVE_BOOKING:
                return await self.async_step_remove_booking()

        return self.async_show_form(
            step_id="user", data_schema=STEP_BOOKING_OPTION_SCHEMA
        )

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
                # Create entry after successful validation
                return self.async_create_entry(title=info["title"], data=user_input)

            return self.async_show_form(
                step_id=CONF_ADD_BOOKING, data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        return self.async_show_form(
            step_id=CONF_ADD_BOOKING, data_schema=STEP_USER_DATA_SCHEMA
        )

    async def async_step_remove_booking(self, user_input=None) -> FlowResult:
        """Handle the remove booking step."""
        # Implement the logic for removing a booking if applicable
        # For now, this is a placeholder
        if user_input is not None:
            # Handle removal logic here
            return self.async_create_entry(title=REMOVE_BOOKING, data=user_input)

        return self.async_show_form(
            step_id=CONF_REMOVE_BOOKING, data_schema=STEP_USER_DATA_SCHEMA
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
