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
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME

from .const import (
    DOMAIN,
    REGIONS,
    CONF_REGION,
    DEFAULT_NAME,
    DWD_REGION_ID,
    ERROR_MESSAGES,
    VERSION,
)
from .api import KleenexPollenRadarApiClient, KleenexPollenRadarApiAuthError
from .dwd_api import get_dwd_data, DWDApiError

_LOGGER = logging.getLogger(__name__)


def get_config_schema(hass: HomeAssistant, user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Get the config flow schema with optional default values.
    
    Args:
        hass: The Home Assistant instance
        user_input: Optional dictionary containing previous user input
        
    Returns:
        Schema for the config flow
    """
    if user_input is None:
        user_input = {}
    
    # Create a sorted list of regions for better UX
    regions = {
        key: details["name"]
        for key, details in sorted(
            REGIONS.items(),
            key=lambda x: x[1]["name"]
        )
    }
    
    return vol.Schema({
        vol.Required(
            CONF_REGION,
            default=user_input.get(CONF_REGION)
        ): vol.In(regions),
        vol.Required(
            CONF_LATITUDE,
            default=user_input.get(CONF_LATITUDE, hass.config.latitude)
        ): config_validation.latitude,
        vol.Required(
            CONF_LONGITUDE,
            default=user_input.get(CONF_LONGITUDE, hass.config.longitude)
        ): config_validation.longitude,
        vol.Optional(
            CONF_NAME,
            default=user_input.get(CONF_NAME, DEFAULT_NAME)
        ): str,
    })


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.
    
    Args:
        hass: The Home Assistant instance
        data: Dictionary containing user input
        
    Returns:
        Dictionary containing validated data
        
    Raises:
        CannotConnect: Error connecting to the API
        InvalidAuth: Invalid authentication
    """
    session = async_get_clientsession(hass)
    
    try:
        if data[CONF_REGION] == "de":
            # For German region, test DWD API
            _LOGGER.debug("Testing DWD API connection for Dresden (Region ID: %s)", DWD_REGION_ID)
            await get_dwd_data()
            _LOGGER.debug("DWD API connection test successful")
        else:
            # For other regions, test Kleenex API
            _LOGGER.debug("Testing Kleenex API connection for region: %s", data[CONF_REGION])
            api = KleenexPollenRadarApiClient(
                session=session,
                region=data[CONF_REGION],
                latitude=data[CONF_LATITUDE],
                longitude=data[CONF_LONGITUDE]
            )
            result = await api.async_get_data()
            if not result:
                _LOGGER.error("No data received from Kleenex API")
                raise InvalidAuth(ERROR_MESSAGES["no_data"])
            _LOGGER.debug("Kleenex API connection test successful")
    except DWDApiError as err:
        _LOGGER.error("DWD API validation error: %s", str(err))
        raise CannotConnect(ERROR_MESSAGES["cannot_connect"]) from err
    except KleenexPollenRadarApiAuthError as err:
        _LOGGER.error("Kleenex API authentication error: %s", str(err))
        raise InvalidAuth(ERROR_MESSAGES["invalid_auth"]) from err
    except Exception as err:
        _LOGGER.error("Unexpected error during validation: %s", str(err))
        raise CannotConnect(ERROR_MESSAGES["unknown"]) from err

    # Use region name for the title if no custom name is provided
    title = data.get(CONF_NAME) or REGIONS[data[CONF_REGION]]["name"]
    return {"title": title}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kleenex pollen."""

    VERSION = VERSION

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step.
        
        Args:
            user_input: Dictionary containing user input if provided
            
        Returns:
            FlowResult containing the next step or entry creation
        """
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=get_config_schema(self.hass),
                errors=errors,
                description_placeholders={
                    "name": DEFAULT_NAME,
                    "version": VERSION,
                }
            )

        # Set unique ID before validation to prevent race conditions
        await self.async_set_unique_id(
            f"{user_input[CONF_REGION]}_{user_input[CONF_LATITUDE]}_{user_input[CONF_LONGITUDE]}"
        )
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

        # If we have errors, show the form again with the errors
        return self.async_show_form(
            step_id="user",
            data_schema=get_config_schema(self.hass, user_input),
            errors=errors,
            description_placeholders={
                "name": DEFAULT_NAME,
                "version": VERSION,
            }
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
