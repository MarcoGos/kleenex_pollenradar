"""Sensor platform for the Pollenradar integration."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging
import asyncio
from homeassistant import config_entries
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from .api import PollenApi
from .const import (
    DEFAULT_SYNC_INTERVAL,
    DOMAIN,
    RETRY_ATTEMPTS,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class PollenDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PollenApi,
        config_entry: config_entries.ConfigEntry | None,
    ) -> None:
        """Initialize."""
        self.api = api
        self.platforms: list[str] = []
        self._hass = hass

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SYNC_INTERVAL),
            config_entry=config_entry,
        )

    async def _async_update_data(self):
        """Update data via library."""
        error = ""
        for attempt in range(1, RETRY_ATTEMPTS):
            try:
                pollen = await self.api.async_get_data()
                raw = self.api.get_raw_data()
                last_updated = datetime.now().replace(
                    tzinfo=ZoneInfo(self._hass.config.time_zone)
                )
                return {
                    "pollen": pollen,
                    "raw": raw,
                    "last_updated": last_updated,
                    "error": "",
                }
            except Exception as e:
                error = str(e)
                await asyncio.sleep(attempt * 2)

        _LOGGER.warning("Warning: All %d attempts to get data failed", RETRY_ATTEMPTS)
        return (self.data or {}) | {"error": error}
