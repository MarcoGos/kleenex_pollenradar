from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import UpdateFailed, DataUpdateCoordinator
import logging
from homeassistant.core import HomeAssistant
from .api import PollenApi
from .const import (
    DEFAULT_SYNC_INTERVAL,
    DOMAIN,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class PollenDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: PollenApi) -> None:
        """Initialize."""
        self.api = api
        self.platforms: list[str] = []
        self.last_updated = None

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
            self.last_updated = datetime.now()
            return data
        except Exception as exception:
            _LOGGER.error(f"Error _async_update_data: {exception}")
            raise UpdateFailed() from exception
