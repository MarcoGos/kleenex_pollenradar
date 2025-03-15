"""Data update coordinator for the Kleenex Pollen Radar integration.

This module manages the data updates for both the Kleenex Pollen Radar API
and the DWD (Deutscher Wetterdienst) API. It handles:
- Initialization of the appropriate API client
- Regular data updates based on region-specific intervals
- Error handling and data validation
- Device information management
"""
from datetime import timedelta
import logging
from typing import Any, Dict, Optional, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import KleenexPollenRadarApiClient, KleenexPollenRadarApiAuthError
from .dwd_api import get_dwd_data, DWDApiError
from .const import (
    DOMAIN,
    DEFAULT_SYNC_INTERVAL,
    MIN_UPDATE_INTERVAL,
    DWD_MANUFACTURER,
    DWD_MODEL,
    DWD_UPDATE_INTERVAL,
    REGIONS,
    ERROR_MESSAGES,
)

_LOGGER = logging.getLogger(__name__)

class PollenDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Pollen data from multiple sources."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Optional[KleenexPollenRadarApiClient],
        region: str,
    ) -> None:
        """Initialize the coordinator.
        
        Args:
            hass: The Home Assistant instance
            client: The Kleenex API client (None for DWD regions)
            region: The region code (e.g., 'de', 'fr', 'uk')
        
        Raises:
            ValueError: If the region is not supported
        """
        self.client = client
        self.region = region
        
        # Validate region and get configuration
        self.region_info = self._validate_region(region)
        
        # Set update interval based on region configuration
        update_interval = self._get_update_interval()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    def _validate_region(self, region: str) -> Dict[str, Any]:
        """Validate the region and return its configuration.
        
        Args:
            region: The region code to validate
            
        Returns:
            Dictionary containing the region configuration
            
        Raises:
            ValueError: If the region is not supported
        """
        if region not in REGIONS:
            raise ValueError(ERROR_MESSAGES["invalid_region"])
            
        region_info = REGIONS[region]
        if not isinstance(region_info, dict):
            raise ValueError(f"Invalid region configuration for {region}")
            
        required_keys = ["name", "url"]
        missing_keys = [key for key in required_keys if key not in region_info]
        if missing_keys:
            raise ValueError(f"Missing required configuration keys for {region}: {missing_keys}")
            
        return region_info

    def _get_update_interval(self) -> timedelta:
        """Get the update interval based on region configuration.
        
        Returns:
            timedelta: The update interval to use
        """
        if self.region == "de":
            interval_seconds = self.region_info.get("update_interval", DWD_UPDATE_INTERVAL)
        else:
            interval_seconds = DEFAULT_SYNC_INTERVAL
            
        # Ensure the interval is not too short
        if interval_seconds < MIN_UPDATE_INTERVAL:
            _LOGGER.warning(
                "Update interval too short (%d seconds), using %d seconds instead",
                interval_seconds,
                MIN_UPDATE_INTERVAL
            )
            interval_seconds = MIN_UPDATE_INTERVAL
            
        return timedelta(seconds=interval_seconds)

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information based on region.
        
        Returns:
            Dictionary containing device information including:
            - identifiers
            - name
            - manufacturer
            - model
        """
        if self.region == "de":
            return {
                "identifiers": {(DOMAIN, f"dwd_{self.region}")},
                "name": "DWD Pollenflug",
                "manufacturer": self.region_info.get("manufacturer", DWD_MANUFACTURER),
                "model": self.region_info.get("model", DWD_MODEL),
            }
        else:
            return {
                "identifiers": {(DOMAIN, f"kleenex_{self.region}")},
                "name": f"Kleenex Pollen Radar {self.region.upper()}",
                "manufacturer": "Kleenex",
                "model": "Pollen Radar",
            }

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the appropriate API.
        
        Returns:
            Dictionary containing the pollen forecast data
            
        Raises:
            ConfigEntryAuthFailed: If authentication fails
            UpdateFailed: If there is an error fetching the data
        """
        try:
            if self.region == "de":
                _LOGGER.debug("Fetching DWD pollen data for Dresden")
                try:
                    data = await get_dwd_data()
                    if not data:
                        raise UpdateFailed(ERROR_MESSAGES["no_data"])
                    _LOGGER.debug("DWD data fetched successfully: %d forecasts", len(data))
                    return {"forecasts": data}
                except DWDApiError as err:
                    _LOGGER.error("DWD API error: %s", str(err))
                    if err.original_error:
                        _LOGGER.debug("Original error: %s", str(err.original_error))
                    raise UpdateFailed(str(err)) from err
            else:
                if not self.client:
                    _LOGGER.error("No Kleenex API client available")
                    raise ConfigEntryAuthFailed(ERROR_MESSAGES["invalid_auth"])
                
                _LOGGER.debug("Fetching Kleenex pollen data for %s", self.region)
                try:
                    data = await self.client.async_get_data()
                    if not data:
                        raise UpdateFailed(ERROR_MESSAGES["no_data"])
                    if "forecasts" not in data:
                        _LOGGER.warning("Unexpected data format from Kleenex API")
                        raise UpdateFailed(ERROR_MESSAGES["parse_error"])
                    _LOGGER.debug("Kleenex data fetched successfully: %d forecasts", len(data["forecasts"]))
                    return data
                except KleenexPollenRadarApiAuthError as err:
                    _LOGGER.error("Authentication error for Kleenex API: %s", str(err))
                    raise ConfigEntryAuthFailed(ERROR_MESSAGES["invalid_auth"]) from err

        except Exception as err:
            _LOGGER.error(
                "Unexpected error fetching %s pollen data: %s",
                "DWD" if self.region == "de" else "Kleenex",
                str(err)
            )
            raise UpdateFailed(ERROR_MESSAGES["unknown"]) from err
