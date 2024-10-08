"""Config flow for Jet2 integration."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.calendar import CalendarEntityFeature
from homeassistant.config_entries import ConfigFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    ADD_BOOKING,
    BOOKING_OPTION,
    CONF_BOOKING_REFERENCE,
    CONF_CALENDARS,
    CONF_DATE_OF_BIRTH,
    CONF_SURNAME,
    DOMAIN,
    REMOVE_BOOKING,
)
from .coordinator import Jet2Coordinator

_LOGGER = logging.getLogger(__name__)

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


async def _get_calendar_entities(hass: HomeAssistant) -> list[str]:
    """Retrieve calendar entities."""
    entity_registry = er.async_get(hass)
    calendar_entities = {}
    for entity_id, entity in entity_registry.entities.items():
        if entity_id.startswith("calendar."):
            calendar_entity = hass.states.get(entity_id)
            if calendar_entity:
                supported_features = calendar_entity.attributes.get(
                    "supported_features", 0
                )

                supports_create_event = (
                    supported_features & CalendarEntityFeature.CREATE_EVENT
                )

                if supports_create_event:
                    calendar_name = entity.original_name or entity_id
                    calendar_entities[entity_id] = calendar_name

    calendar_entities["None"] = "Create a new calendar"
    return calendar_entities


def is_date_valid_format(value: str) -> bool:
    """Validate date input."""
    try:
        datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        return False
    else:
        return True


@callback
def async_get_options_flow(config_entry):
    """Jet2 flow handler."""
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

        errors: dict[str, str] = {}

        calendar_entities = await _get_calendar_entities(self.hass)

        user_input = user_input or {}

        STEP_USER_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(
                    CONF_BOOKING_REFERENCE,
                    default=user_input.get(CONF_BOOKING_REFERENCE, ""),
                ): cv.string,
                vol.Required(
                    CONF_DATE_OF_BIRTH, default=user_input.get(CONF_DATE_OF_BIRTH, "")
                ): cv.string,
                vol.Required(
                    CONF_SURNAME, default=user_input.get(CONF_SURNAME, "")
                ): cv.string,
                vol.Required(
                    CONF_CALENDARS, default=user_input.get(CONF_CALENDARS, [])
                ): cv.multi_select(calendar_entities),
            }
        )

        if user_input:
            entries = self.hass.config_entries.async_entries(DOMAIN)

            if any(
                entry.data.get(CONF_BOOKING_REFERENCE)
                == user_input.get(CONF_BOOKING_REFERENCE)
                for entry in entries
            ):
                errors["base"] = "booking_exists"

            if not user_input.get(CONF_CALENDARS):
                errors["base"] = "no_calendar_selected"

            if not is_date_valid_format(user_input.get(CONF_DATE_OF_BIRTH)):
                errors["base"] = "invalid_date_format"

            if not errors:
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
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
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
                _LOGGER.error("Failed to import booking: %s", e)
                return self.async_abort(reason="import_failed")

        # Explicitly handle the case where import_data is None
        return self.async_abort(reason="no_import_data")


class Jet2FlowHandler(config_entries.OptionsFlow):
    """Jet2 flow handler."""

    def __init__(self, config_entry) -> None:
        """Init."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Init."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
