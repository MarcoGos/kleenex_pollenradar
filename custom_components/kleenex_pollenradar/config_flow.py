"""Config flow for Kleenex pollen integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    REGIONS,
    CONF_GET_CONTENT_BY,
    CONF_REGION,
    CONF_NAME,
    CONF_CITY,
    GetContentBy,
    Regions,
)
from .api import PollenApi, DNSError

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kleenex pollen."""

    VERSION = 1
    region: str = ""
    name: str = ""
    get_content_by: GetContentBy = GetContentBy.CITY
    city: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self.region = user_input[CONF_REGION]
            self.name = user_input[CONF_NAME]
            self.city = user_input[CONF_CITY]
            if self.region == Regions.ITALY.value:
                self.get_content_by = GetContentBy.CITY_ITALY
            else:
                self.get_content_by = GetContentBy.CITY
            user_input[CONF_GET_CONTENT_BY] = self.get_content_by.value

            await self.async_set_unique_id(self.name)
            self._abort_if_unique_id_configured()

            try:
                session = async_get_clientsession(self.hass)
                api = PollenApi(
                    session=session,
                    region=self.region,
                    get_content_by=self.get_content_by,
                    city=self.city,
                )
                data = await api.async_get_data()
                if not data or not data.get("pollen"):
                    raise InvalidAuth
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except DNSError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=self.name, data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_REGION, default=self.region): vol.In(
                    {key: details["name"] for key, details in REGIONS.items()}
                ),
                vol.Required(CONF_CITY, default=self.city): str,
                vol.Required(
                    CONF_NAME, default=self.name or self.hass.config.location_name
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
