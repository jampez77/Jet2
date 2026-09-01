"""Config flow for the Jet2 integration."""

from datetime import datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.calendar import CalendarEntityFeature
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_BOOKING_REFERENCE,
    CONF_CALENDARS,
    CONF_DATE_OF_BIRTH,
    CONF_SURNAME,
    DOMAIN,
)
from .coordinator import InvalidAuth, Jet2ConnectionError, async_fetch_booking

_LOGGER = logging.getLogger(__name__)


async def _get_calendar_entities(hass: HomeAssistant) -> dict[str, str]:
    """Return calendars that support creating events."""
    entity_registry = er.async_get(hass)
    calendar_entities: dict[str, str] = {}
    for entity_id, entity in entity_registry.entities.items():
        if not entity_id.startswith("calendar."):
            continue

        calendar_state = hass.states.get(entity_id)
        if calendar_state is None:
            continue

        supported_features = calendar_state.attributes.get("supported_features", 0)
        if supported_features & CalendarEntityFeature.CREATE_EVENT:
            calendar_entities[entity_id] = entity.original_name or entity_id

    calendar_entities["None"] = "Create a new calendar"
    return calendar_entities


def is_date_valid_format(value: str | None) -> bool:
    """Validate a date in the format expected by Jet2."""
    if value is None:
        return False
    try:
        datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        return False
    return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate that the booking can be retrieved."""
    await async_fetch_booking(async_get_clientsession(hass), data)
    return {"title": str(data[CONF_BOOKING_REFERENCE]).upper()}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jet2."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        calendar_entities = await _get_calendar_entities(self.hass)
        user_input = user_input or {}

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_BOOKING_REFERENCE,
                    default=user_input.get(CONF_BOOKING_REFERENCE, ""),
                ): cv.string,
                vol.Required(
                    CONF_DATE_OF_BIRTH,
                    default=user_input.get(CONF_DATE_OF_BIRTH, ""),
                ): cv.string,
                vol.Required(
                    CONF_SURNAME,
                    default=user_input.get(CONF_SURNAME, ""),
                ): cv.string,
                vol.Required(
                    CONF_CALENDARS,
                    default=user_input.get(CONF_CALENDARS, []),
                ): cv.multi_select(calendar_entities),
            }
        )

        if user_input:
            user_input = {
                **user_input,
                CONF_BOOKING_REFERENCE: user_input[CONF_BOOKING_REFERENCE]
                .strip()
                .upper(),
                CONF_DATE_OF_BIRTH: user_input[CONF_DATE_OF_BIRTH].strip(),
                CONF_SURNAME: user_input[CONF_SURNAME].strip(),
            }

            if not user_input[CONF_CALENDARS]:
                errors["base"] = "no_calendar_selected"
            elif not is_date_valid_format(user_input[CONF_DATE_OF_BIRTH]):
                errors["base"] = "invalid_date_format"

            if not errors:
                await self.async_set_unique_id(user_input[CONF_BOOKING_REFERENCE])
                self._abort_if_unique_id_configured()
                try:
                    info = await validate_input(self.hass, user_input)
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Jet2ConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected exception while validating Jet2")
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(
        self, import_data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle an import initiated by the add-booking service."""
        if import_data is None:
            return self.async_abort(reason="no_import_data")

        reference = str(import_data[CONF_BOOKING_REFERENCE]).strip().upper()
        await self.async_set_unique_id(reference)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=reference,
            data={**import_data, CONF_BOOKING_REFERENCE: reference},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return Jet2OptionsFlow()


class Jet2OptionsFlow(config_entries.OptionsFlow):
    """Handle Jet2 options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the empty options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
