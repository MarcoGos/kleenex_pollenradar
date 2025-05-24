"""The Kleenex pollenradar integration."""

from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .api import PollenApi
from .const import DOMAIN, NAME, PLATFORMS, CONF_REGION, MODEL, MANUFACTURER
from .coordinator import PollenDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Kleenex pollen from a config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    region = config_entry.data[CONF_REGION]
    latitude = config_entry.data[CONF_LATITUDE]
    longitude = config_entry.data[CONF_LONGITUDE]

    _LOGGER.debug("entry.data: %s", config_entry.data)

    session = async_get_clientsession(hass)
    api = PollenApi(
        session=session,
        region=region,
        latitude=latitude,
        longitude=longitude,
    )

    device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, f"{latitude}x{longitude}")},
        name=f"{NAME} ({config_entry.data['name']})",
        model=MODEL,
        manufacturer=MANUFACTURER,
    )

    hass.data[DOMAIN][config_entry.entry_id] = coordinator = (
        PollenDataUpdateCoordinator(hass, api=api, device_info=device_info)
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(config_entry.entry_id)
