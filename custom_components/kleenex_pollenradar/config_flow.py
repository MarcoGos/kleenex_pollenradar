"""Config flow for Kleenex pollen integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .const import DOMAIN, REGIONS, CONF_REGION
from .api import PollenApi

_LOGGER = logging.getLogger(__name__)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self) -> None:
        """Initialize."""

    async def authenticate(
        self, session, region: str, latitude: float, longitude: float
    ) -> bool:
        """Test if we can find data for the given position."""
        _LOGGER.info(f"authenticate called with {latitude} {longitude}")
        api = PollenApi(
            session=session, region=region, latitude=latitude, longitude=longitude
        )
        return not not await api.async_get_data()


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    hub = PlaceholderHub()
    if not await hub.authenticate(
        session, data[CONF_REGION], data[CONF_LATITUDE], data[CONF_LONGITUDE]
    ):
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": data["name"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kleenex pollen."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        STEP_USER_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_REGION): vol.In(
                    {key: details["name"] for key, details in REGIONS.items()}
                ),
                vol.Required("name", default=self.hass.config.location_name): str,
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): config_validation.latitude,
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): config_validation.longitude,
            }
        )

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        await self.async_set_unique_id(user_input["name"])
        self._abort_if_unique_id_configured()

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
