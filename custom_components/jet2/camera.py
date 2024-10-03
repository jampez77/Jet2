"""Camera sensor for Jet2."""

import requests

from homeassistant.components.camera import Camera, CameraEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BOOKING_REFERENCE, DOMAIN
from .coordinator import Jet2Coordinator

SENSOR_DESCRIPTION = CameraEntityDescription(
    key="accommodationImages",
    name="Accomodation Images",
    icon="mdi:camera-burst",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]

    session = async_get_clientsession(hass)

    coordinator = Jet2Coordinator(hass, session, config)

    await coordinator.async_refresh()

    name = config[CONF_BOOKING_REFERENCE]

    sensors = [Jet2CameraSensor(coordinator, name, SENSOR_DESCRIPTION)]
    async_add_entities(sensors, update_before_add=True)


class Jet2CameraSensor(CoordinatorEntity[Jet2Coordinator], Camera):
    """Representation of a Camera entity."""

    def __init__(
        self,
        coordinator: Jet2Coordinator,
        name: str,
        description: CameraEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        Camera.__init__(self)  # Initialize the Camera base class

        self.success = bool(coordinator.data.get("success"))
        self._name = "Accommodation Images"
        self._image_urls = None

        if self.success:
            self.data = coordinator.data.get("data")

            if "hotel" in self.data:
                self._name = self.data["hotel"]["name"]
            elif "resort" in self.data:
                self._name = self.data["resort"]
            elif "area" in self.data:
                self._name = self.data["area"]
            elif "region" in self.data:
                self._name = self.data["region"]

            self.entity_description = description
            self._current_index = 0
            self._image_urls = self.data["accommodationImages"]

            # Setup unique ID and entity ID
            self._attr_unique_id = f"{DOMAIN}-{name}-{description.key}-camera".lower()
            self.entity_id = f"camera.{DOMAIN}_{name}_{description.key}".lower()

            # Set up device info
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{name}")},
                manufacturer="Jet2",
                model=self.data.get("holidayType"),
                name=name.upper(),
                configuration_url="https://github.com/jampez77/Jet2/",
            )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self.success and len(self._image_urls) > 0)

    @property
    def name(self) -> str:
        """Return the name of the camera."""
        return self._name

    @property
    def is_streaming(self) -> bool:
        """Return True if the camera is streaming."""
        return bool(self.success and len(self._image_urls) > 0)

    def camera_image(self, width: int = 0, height: int = 0) -> bytes:
        """Return the image to serve for the camera entity."""
        if not self.success or self._image_urls is None:
            return None

        # Get the current image URL
        image_url = (
            "https://www.jet2holidays.com" + self._image_urls[self._current_index]
        )

        # Rotate to the next image
        self._current_index = (self._current_index + 1) % len(self._image_urls)

        # Fetch and return the image content
        response = requests.get(image_url, timeout=10)
        return response.content
