"""Camera platform for the Jet2 integration."""

from typing import override
from urllib.parse import urljoin

from aiohttp import ClientError, ClientTimeout

from homeassistant.components.camera import Camera, CameraEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BOOKING_REFERENCE, DOMAIN
from .coordinator import Jet2ConfigEntry, Jet2Coordinator

SENSOR_DESCRIPTION = CameraEntityDescription(
    key="accommodationImages",
    name="Accommodation Images",
    icon="mdi:camera-burst",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Jet2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Jet2 accommodation camera."""
    async_add_entities(
        [
            Jet2CameraSensor(
                entry.runtime_data,
                entry.data[CONF_BOOKING_REFERENCE],
                SENSOR_DESCRIPTION,
            )
        ]
    )


class Jet2CameraSensor(CoordinatorEntity[Jet2Coordinator], Camera):
    """Rotate through accommodation images from a Jet2 booking."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Jet2Coordinator,
        booking_reference: str,
        description: CameraEntityDescription,
    ) -> None:
        """Initialize the camera."""
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self.entity_description = description
        self._attr_unique_id = (
            f"{DOMAIN}-{booking_reference}-{description.key}-camera".lower()
        )
        self._current_index = 0

        booking = coordinator.data["data"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, booking_reference)},
            manufacturer="Jet2",
            model=booking.get("holidayType"),
            name=booking_reference.upper(),
            configuration_url="https://github.com/jampez77/Jet2/",
        )

    @property
    @override
    def available(self) -> bool:
        """Return whether an accommodation image is available."""
        return super().available and bool(self._image_urls)

    @property
    def _image_urls(self) -> list[str]:
        """Return the current image URLs."""
        images = self.coordinator.data["data"].get("accommodationImages")
        if not isinstance(images, list):
            return []
        return [image for image in images if isinstance(image, str)]

    @override
    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the next accommodation image."""
        image_urls = self._image_urls
        if not image_urls:
            return None

        image_path = image_urls[self._current_index % len(image_urls)]
        self._current_index = (self._current_index + 1) % len(image_urls)
        image_url = urljoin("https://www.jet2holidays.com/", image_path)

        try:
            async with self.coordinator.session.get(
                image_url, timeout=ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                return await response.read()
        except (ClientError, TimeoutError) as err:
            raise HomeAssistantError(
                "Unable to fetch the Jet2 accommodation image"
            ) from err
