from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging
from homeassistant.helpers.update_coordinator import UpdateFailed, DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import HomeAssistant
from .api import PollenApi
from .const import (
    DEFAULT_SYNC_INTERVAL,
    DOMAIN,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class PollenDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: PollenApi, device_info: DeviceInfo) -> None:
        """Initialize."""
        self.api = api
        self.platforms: list[str] = []
        self.last_updated = None
        self.device_info = device_info
        self._hass = hass
        self.latitude = api.latitude
        self.longitude = api.longitude
        self.region = api.region
        self.raw: str = ''

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SYNC_INTERVAL),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            data = await self.api.async_get_data()
            self.raw = self.api.get_raw_data()
            self.last_updated = datetime.now().replace(tzinfo=ZoneInfo(self._hass.config.time_zone))
            return data
        except Exception as exception:
            _LOGGER.error(f"Error _async_update_data: {exception}")
            raise UpdateFailed() from exception
