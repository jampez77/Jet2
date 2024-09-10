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
from .const import (
    HOST,
    CONF_BOOKING_REFERENCE,
    CONF_DATE_OF_BIRTH,
    CONF_SURNAME,
    CONF_BOOKINGREFERENCE,
    CONF_DATEOFBIRTH
)

_LOGGER = logging.getLogger(__name__)


class Jet2Coordinator(DataUpdateCoordinator):
    """Data coordinator."""

    def __init__(self, hass: HomeAssistant, session, data: dict) -> None:
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
        """Fetch data from API endpoint."""
        try:
            resp = await self.session.request(
                method="POST",
                url=HOST,
                json={
                    CONF_BOOKINGREFERENCE: self.booking_reference,
                    CONF_DATEOFBIRTH: self.date_of_birth,
                    CONF_SURNAME: self.surname,
                },
                headers={"Content-Type": CONTENT_TYPE_JSON},
            )

            if resp.status == 401:
                raise InvalidAuth("Invalid authentication credentials")
            if resp.status == 429:
                raise APIRatelimitExceeded("API rate limit exceeded.")

            body = await resp.json()

            # Validate response structure
            if not isinstance(body, dict):
                raise ValueError("Unexpected response format")

            return body

        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except Jet2Error as err:
            raise UpdateFailed(str(err)) from err
        except ValueError as err:
            _LOGGER.exception("Value error occurred: %s", err)
            raise UpdateFailed(f"Unexpected response: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected exception: %s", err)
            raise UnknownError from err


class Jet2Error(HomeAssistantError):
    """Base error."""


class InvalidAuth(Jet2Error):
    """Raised when invalid authentication credentials are provided."""


class APIRatelimitExceeded(Jet2Error):
    """Raised when the API rate limit is exceeded."""


class UnknownError(Jet2Error):
    """Raised when an unknown error occurs."""
