"""The Kleenex pollenradar integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PollenApi
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_REGION,
    CONF_GET_CONTENT_BY,
    CONF_CITY,
    GetContentBy,
)
from .coordinator import PollenDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Kleenex pollen from a config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    api = PollenApi(
        session=session,
        region=config_entry.data[CONF_REGION],
        get_content_by=GetContentBy(
            config_entry.data.get(CONF_GET_CONTENT_BY, GetContentBy.CITY.value)
        ),
        city=config_entry.data.get(CONF_CITY, ""),
    )

    hass.data[DOMAIN][config_entry.entry_id] = coordinator = (
        PollenDataUpdateCoordinator(hass, api=api, config_entry=config_entry)
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
