"""Data coordinator for the Jet2 integration."""

from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Any, override

from aiohttp import ClientError, ClientSession, ClientTimeout

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Jet2ConfigEntry

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BOOKING_REFERENCE,
    CONF_BOOKINGREFERENCE,
    CONF_DATE_OF_BIRTH,
    CONF_DATEOFBIRTH,
    CONF_SURNAME,
    DOMAIN,
    HOST,
)

_LOGGER = logging.getLogger(__name__)

type Jet2Response = dict[str, Any]


async def async_fetch_booking(
    session: ClientSession, data: Mapping[str, Any]
) -> Jet2Response:
    """Fetch and validate a booking from Jet2."""
    try:
        async with session.post(
            HOST,
            json={
                CONF_BOOKINGREFERENCE: data[CONF_BOOKING_REFERENCE],
                CONF_DATEOFBIRTH: data[CONF_DATE_OF_BIRTH],
                CONF_SURNAME: data[CONF_SURNAME],
            },
            headers={
                "Accept": CONTENT_TYPE_JSON,
                "Content-Type": CONTENT_TYPE_JSON,
            },
            timeout=ClientTimeout(total=30),
        ) as response:
            if response.status in (401, 403):
                raise InvalidAuth("The Jet2 booking details were rejected")
            if response.status == 429:
                raise APIRateLimitExceeded("The Jet2 API rate limit was exceeded")

            response.raise_for_status()
            body = await response.json()
    except Jet2Error:
        raise
    except (ClientError, TimeoutError, ValueError) as err:
        raise Jet2ConnectionError("Unable to retrieve the Jet2 booking") from err

    if not isinstance(body, dict):
        raise Jet2ConnectionError("Jet2 returned an unexpected response")

    if body.get("success") is not True or not isinstance(body.get("data"), dict):
        raise InvalidAuth("The Jet2 booking details were rejected")

    return body


class Jet2Coordinator(DataUpdateCoordinator[Jet2Response]):
    """Coordinate booking updates from Jet2."""

    config_entry: Jet2ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: Jet2ConfigEntry,
        session: ClientSession,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(days=1),
        )
        self.session = session

    @override
    async def _async_update_data(self) -> Jet2Response:
        """Fetch the latest booking data."""
        try:
            return await async_fetch_booking(self.session, self.config_entry.data)
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except Jet2Error as err:
            raise UpdateFailed(str(err)) from err


type Jet2ConfigEntry = ConfigEntry[Jet2Coordinator]


class Jet2Error(HomeAssistantError):
    """Base Jet2 error."""


class InvalidAuth(Jet2Error):
    """Raised when booking authentication is rejected."""


class APIRateLimitExceeded(Jet2Error):
    """Raised when the API rate limit is exceeded."""


class Jet2ConnectionError(Jet2Error):
    """Raised when Jet2 cannot be reached or returns invalid data."""
