"""Config flow for Kleenex pollen integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .const import DOMAIN, REGIONS, CONF_REGION, CONF_NAME
from .api import PollenApi, DNSError

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kleenex pollen."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            try:
                session = async_get_clientsession(self.hass)
                api = PollenApi(
                    session=session,
                    region=user_input[CONF_REGION],
                    latitude=user_input[CONF_LATITUDE],
                    longitude=user_input[CONF_LONGITUDE],
                )
                if not await api.async_get_data():
                    raise InvalidAuth
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except DNSError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_REGION): vol.In(
                    {key: details["name"] for key, details in REGIONS.items()}
                ),
                vol.Required(CONF_NAME, default=self.hass.config.location_name): str,
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): config_validation.latitude,
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): config_validation.longitude,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        errors: dict[str, str] | None = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])  # type: ignore

        if user_input is not None and entry:
            try:
                session = async_get_clientsession(self.hass)
                api = PollenApi(
                    session=session,
                    region=user_input[CONF_REGION],
                    latitude=user_input[CONF_LATITUDE],
                    longitude=user_input[CONF_LONGITUDE],
                )
                if not await api.async_get_data():
                    raise InvalidAuth
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except DNSError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                device_registry = dr.async_get(self.hass)
                device = device_registry.async_get_device(
                    identifiers={
                        (
                            DOMAIN,
                            f"{entry.data[CONF_LATITUDE]}x{entry.data[CONF_LONGITUDE]}",
                        )
                    }
                )
                if device:
                    device_registry.async_update_device(
                        device_id=device.id,
                        remove_config_entry_id=entry.entry_id,
                    )
                self.hass.config_entries.async_update_entry(
                    entry,  # type: ignore
                    data=entry.data | user_input,  # type: ignore
                    title=user_input[CONF_NAME],
                )
                await self.hass.config_entries.async_reload(entry.entry_id)  # type: ignore
                return self.async_abort(reason="reconfigure_successful")

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): config_validation.latitude,
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): config_validation.longitude,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=data_schema,
                suggested_values=entry.data | (user_input or {}),  # type: ignore
            ),
            description_placeholders={"name": entry.title},  # type: ignore
            errors=errors,
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
