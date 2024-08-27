import requests
from homeassistant.components.camera import Camera
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.camera import CameraEntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from typing import Any
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_BOOKING_REFERENCE
from .coordinator import Jet2Coordinator
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

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
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]

    session = async_get_clientsession(hass)

    coordinator = Jet2Coordinator(hass, session, config)

    await coordinator.async_refresh()

    name = config[CONF_BOOKING_REFERENCE]

    sensors = [Jet2CameraSensor(coordinator, name, SENSOR_DESCRIPTION)]
    async_add_entities(sensors, update_before_add=True)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        _: DiscoveryInfoType | None = None,) -> None:
    """Set up the custom camera platform."""

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
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)  # Initialize the Camera base class
        self.data = coordinator.data.get('data')

        if "hotel" in self.data:
            self._name = self.data["hotel"]["name"]
        elif "resort" in self.data:
            self._name = self.data["resort"]
        elif "area" in self.data:
            self._name = self.data["area"]
        elif "region" in self.data:
            self._name = self.data["region"]
        else:
            self._name = "Accommodation Images"

        self.entity_description = description
        self._current_index = 0
        self._image_urls = self.data["accommodationImages"]

        # Setup unique ID and entity ID
        self._attr_unique_id = f"{DOMAIN}-{name}-{description.key}-camera".lower()
        self.entity_id = f"camera.{DOMAIN}_{name}_{description.key}".lower()

        # Set up device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{name}")},
            manufacturer='Jet2 - ' + self.data.get("holidayType"),
            name=name.upper(),
            configuration_url="https://github.com/jampez77/Jet2/",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self.coordinator.data.get('success') and len(self._image_urls) > 0)

    @property
    def name(self) -> str:
        """Return the name of the camera."""
        return self._name

    @property
    def is_streaming(self) -> bool:
        """Return True if the camera is streaming."""
        return bool(len(self._image_urls) > 0)

    def camera_image(self, width: int = None, height: int = None) -> bytes:
        """Return the image to serve for the camera entity."""
        if not self._image_urls:
            return None

        # Get the current image URL
        image_url = "https://www.jet2holidays.com" + \
            self._image_urls[self._current_index]

        # Rotate to the next image
        self._current_index = (self._current_index + 1) % len(self._image_urls)

        # Fetch and return the image content
        response = requests.get(image_url, timeout=10)
        return response.content
