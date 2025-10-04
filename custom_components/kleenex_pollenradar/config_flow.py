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

from .const import (
    DOMAIN,
    REGIONS,
    CONF_GET_CONTENT_BY,
    CONF_REGION,
    CONF_NAME,
    CONF_CITY,
    GetContentBy,
)
from .api import PollenApi, DNSError

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kleenex pollen."""

    VERSION = 1
    region: str = ""
    name: str = ""
    get_content_by: GetContentBy = GetContentBy.LAT_LNG
    city: str = ""
    latitude: float = 0.0
    longitude: float = 0.0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self.region = user_input[CONF_REGION]
            self.name = user_input[CONF_NAME]
            self.get_content_by = GetContentBy(user_input.get(CONF_GET_CONTENT_BY, None))
            if self.get_content_by == GetContentBy.CITY:
                return await self.async_step_city()
            else:
                return await self.async_step_lat_lng()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_REGION): vol.In(
                    {key: details["name"] for key, details in REGIONS.items()}
                ),
                vol.Required(CONF_NAME, default=self.hass.config.location_name): str,
                vol.Required(CONF_GET_CONTENT_BY, default=GetContentBy.CITY): vol.In(
                    {
                        GetContentBy.CITY.value: "City",
                        GetContentBy.LAT_LNG.value: "Latitude / Longitude",
                    }
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_lat_lng(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self.latitude = user_input[CONF_LATITUDE]
            self.longitude = user_input[CONF_LONGITUDE]
            return await self.async_step_final()

        step_user_data_schema = vol.Schema(
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
            step_id="lat_lng", data_schema=step_user_data_schema
        )

    async def async_step_city(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self.city = user_input[CONF_CITY]
            return await self.async_step_final()

        step_user_data_schema = vol.Schema({vol.Required(CONF_CITY, default=""): str})

        return self.async_show_form(step_id="city", data_schema=step_user_data_schema)

    async def async_step_final(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the final step."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(self.name)
            self._abort_if_unique_id_configured()
            user_input[CONF_REGION] = self.region
            user_input[CONF_NAME] = self.name
            user_input[CONF_GET_CONTENT_BY] = self.get_content_by.value
            user_input[CONF_CITY] = self.city
            user_input[CONF_LATITUDE] = self.latitude
            user_input[CONF_LONGITUDE] = self.longitude
            try:
                session = async_get_clientsession(self.hass)
                api = PollenApi(
                    session=session,
                    region=self.region,
                    get_content_by=self.get_content_by,
                    latitude=self.latitude,
                    longitude=self.longitude,
                    city=self.city,
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
                return self.async_create_entry(title=self.name, data=user_input)

        data_schema = vol.Schema({})

        return self.async_show_form(
            step_id="final", data_schema=data_schema, errors=errors, last_step=True
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
                if CONF_LATITUDE not in user_input and CONF_LONGITUDE not in user_input and CONF_CITY not in user_input:
                    user_input[CONF_LATITUDE] = self.hass.config.latitude
                    user-input[CONF_LONGITUDE] = self.hass.config.longitude
                api = PollenApi(
                    session=session,
                    region=entry.data[CONF_REGION],
                    get_content_by=GetContentBy(entry.data.get(CONF_GET_CONTENT_BY, GetContentBy.LAT_LNG),
                    latitude=user_input.get(CONF_LATITUDE, 0.0),
                    longitude=user_input.get(CONF_LONGITUDE, 0.0),
                    city=user_input.get(CONF_CITY, ""),
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
                if (
                    user_input.get(CONF_LATITUDE, 0.0)
                    != entry.data.get(CONF_LATITUDE, 0.0)
                    or user_input.get(CONF_LONGITUDE, 0.0)
                    != entry.data.get(CONF_LONGITUDE, 0.0)
                    or user_input.get(CONF_CITY, "") != entry.data.get(CONF_CITY, "")
                ):
                    device_registry = dr.async_get(self.hass)
                    device = device_registry.async_get_device(
                        identifiers={
                            (
                                DOMAIN,
                                f"{entry.data[CONF_NAME]}",
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
                    title=entry.data[CONF_NAME],
                )
                await self.hass.config_entries.async_reload(entry.entry_id)  # type: ignore
                return self.async_abort(reason="reconfigure_successful")

        if (
            entry
            and GetContentBy(entry.data.get(CONF_GET_CONTENT_BY, GetContentBy.LAT_LNG)) == GetContentBy.LAT_LNG
        ):
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
        else:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_CITY, ""): str,
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
