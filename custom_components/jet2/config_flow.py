"""Config flow for Jet2 integration."""
from __future__ import annotations

import logging
from typing import Any, Dict
from datetime import datetime
import voluptuous as vol
from homeassistant.components.calendar import CalendarEntityFeature
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from .coordinator import Jet2Coordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from .const import (
    DOMAIN,
    CONF_BOOKING_REFERENCE,
    CONF_DATE_OF_BIRTH,
    CONF_SURNAME,
    BOOKING_OPTION,
    ADD_BOOKING,
    REMOVE_BOOKING,
    CONF_ADD_BOOKING,
    CONF_REMOVE_BOOKING,
    CONF_BOOKING_REMOVED,
    CONF_CALENDARS
)

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
    entity_registry = async_get(hass)
    calendar_entities = {}
    for entity_id, entity in entity_registry.entities.items():
        if entity_id.startswith("calendar."):
            calendar_entity = hass.states.get(entity_id)
            if calendar_entity:
                supported_features = calendar_entity.attributes.get(
                    'supported_features', 0)

                supports_create_event = supported_features & CalendarEntityFeature.CREATE_EVENT

                if supports_create_event:
                    calendar_name = entity.original_name or entity_id
                    calendar_entities[entity_id] = calendar_name

    calendar_entities["None"] = "Create a new calendar"
    return calendar_entities


def is_date_valid_format(value: str) -> bool:
    try:
        datetime.strptime(value, "%d/%m/%Y")
        return True
    except ValueError:
        return False


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

        errors: dict[str, str] = {}

        calendar_entities = await _get_calendar_entities(self.hass)

        user_input = user_input or {}

        STEP_USER_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_BOOKING_REFERENCE, default=user_input.get(CONF_BOOKING_REFERENCE, "")): cv.string,
                vol.Required(CONF_DATE_OF_BIRTH, default=user_input.get(CONF_DATE_OF_BIRTH, "")): cv.string,
                vol.Required(CONF_SURNAME, default=user_input.get(CONF_SURNAME, "")): cv.string,
                vol.Required(CONF_CALENDARS, default=user_input.get(CONF_CALENDARS, [])): cv.multi_select(calendar_entities),
            }
        )

        if user_input:

            entries = self.hass.config_entries.async_entries(DOMAIN)

            if any(entry.data.get(CONF_BOOKING_REFERENCE) == user_input.get(CONF_BOOKING_REFERENCE) for entry in entries):
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
                _LOGGER.error(f"Failed to import booking: {e}")
                return self.async_abort(reason="import_failed")


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
