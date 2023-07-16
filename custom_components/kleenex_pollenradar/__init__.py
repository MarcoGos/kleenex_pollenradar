"""The Kleenex pollenradar integration."""
from __future__ import annotations

from typing import Any

from .api import PollenApi
from .const import DOMAIN, PLATFORMS, CONF_REGION

import logging
from homeassistant.config_entries import ConfigEntry, ConfigType

from homeassistant.core import HomeAssistant
from homeassistant.core import Config
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .coordinator import PollenDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Any) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kleenex pollen from a config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    _LOGGER.debug(f"entry.data: {entry.data}")

    session = async_get_clientsession(hass)
    api = PollenApi(
        session=session,
        region=entry.data[CONF_REGION],
        latitude=entry.data[CONF_LATITUDE],
        longitude=entry.data[CONF_LONGITUDE],
    )

    coordinator = PollenDataUpdateCoordinator(hass, api=api)
    _LOGGER.debug("Trying to perform async_refresh")
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    _LOGGER.debug(f"Info about entry: {entry.entry_id}")

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        _LOGGER.debug(f"Adding platform: {platform}")
        coordinator.platforms.append(platform)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
