"""Jet2 Coordinator."""
from datetime import timedelta
import logging
from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import HOST, CONF_BOOKING_REFERENCE, CONF_DATE_OF_BIRTH, CONF_SURNAME

_LOGGER = logging.getLogger(__name__)


class Jet2Coordinator(DataUpdateCoordinator):
    """Data coordinator."""

    def __init__(self, hass: HomeAssistant, session, data) -> None:
        """Initialize coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Jet2",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=300),
        )
        self.session = session
        self.booking_reference = data[CONF_BOOKING_REFERENCE]
        self.date_of_birth = data[CONF_DATE_OF_BIRTH]
        self.surname = data[CONF_SURNAME]

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            resp = await self.session.request(
                method="POST",
                url=HOST,
                json={
                    CONF_BOOKING_REFERENCE: self.booking_reference,
                    CONF_DATE_OF_BIRTH: self.date_of_birth,
                    CONF_SURNAME: self.surname,
                },
            )
            body = await resp.json()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except Jet2Error as err:
            raise UpdateFailed(str(err)) from err
        except ValueError as err:
            err_str = str(err)

            if "Invalid authentication credentials" in err_str:
                raise InvalidAuth from err
            if "API rate limit exceeded." in err_str:
                raise APIRatelimitExceeded from err

            _LOGGER.exception("Unexpected exception")
            raise UnknownError from err

        return body


class Jet2Error(HomeAssistantError):
    """Base error."""


class InvalidAuth(Jet2Error):
    """Raised when invalid authentication credentials are provided."""


class APIRatelimitExceeded(Jet2Error):
    """Raised when the API rate limit is exceeded."""


class UnknownError(Jet2Error):
    """Raised when an unknown error occurs."""
