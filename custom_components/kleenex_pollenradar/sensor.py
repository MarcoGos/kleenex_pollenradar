"""Sensor platform for the Pollenradar integration."""

import logging

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)

from .coordinator import PollenDataUpdateCoordinator
from .const import DOMAIN, NAME

_LOGGER: logging.Logger = logging.getLogger(__package__)


def get_sensor_descriptions() -> list[SensorEntityDescription]:  # type: ignore
    """Return a list of sensor descriptions."""
    level_options = ["low", "moderate", "high", "very-high"]
    descriptions: list[SensorEntityDescription] = [
        SensorEntityDescription(
            key="trees",
            translation_key="trees",
            icon="mdi:tree-outline",
            state_class="measurement",
            native_unit_of_measurement="ppm",
        ),
        SensorEntityDescription(
            key="trees_level",
            translation_key="trees_level",
            device_class=SensorDeviceClass.ENUM,
            options=level_options,
        ),
        SensorEntityDescription(
            key="grass",
            translation_key="grass",
            icon="mdi:grass",
            state_class="measurement",
            native_unit_of_measurement="ppm",
        ),
        SensorEntityDescription(
            key="grass_level",
            translation_key="grass_level",
            device_class=SensorDeviceClass.ENUM,
            options=level_options,
        ),
        SensorEntityDescription(
            key="weeds",
            translation_key="weeds",
            icon="mdi:flower-pollen",
            state_class="measurement",
            native_unit_of_measurement="ppm",
        ),
        SensorEntityDescription(
            key="weeds_level",
            translation_key="weeds_level",
            device_class=SensorDeviceClass.ENUM,
            options=level_options,
        ),
        SensorEntityDescription(
            key="date",
            translation_key="date",
            icon="mdi:calendar",
            device_class=SensorDeviceClass.DATE,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        SensorEntityDescription(
            key="last_updated",
            translation_key="last_updated",
            icon="mdi:clock-outline",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        SensorEntityDescription(
            key="latitude",
            translation_key="latitude",
            icon="mdi:latitude",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="longitude",
            translation_key="longitude",
            icon="mdi:longitude",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="region",
            translation_key="region",
            icon="mdi:earth",
            device_class=SensorDeviceClass.ENUM,
            entity_category=EntityCategory.DIAGNOSTIC,
            options=["fr", "it", "nl", "uk", "us"],
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key="error",
            translation_key="error",
            icon="mdi:alert-circle-outline",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
    ]
    return descriptions


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: PollenDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[KleenexSensor] = []

    for description in get_sensor_descriptions():
        entities.append(
            KleenexSensor(
                coordinator=coordinator,
                entry_id=config_entry.entry_id,
                description=description,
            )
        )
    async_add_entities(entities)


class KleenexSensor(CoordinatorEntity[PollenDataUpdateCoordinator], SensorEntity):
    """Representation of a sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PollenDataUpdateCoordinator,
        entry_id: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}-{NAME}{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        key = self.entity_description.key
        pollen = self.coordinator.data.get("pollen", {})
        current = pollen[0] if pollen else {}
        if self.coordinator.data.get(key, None) is not None:
            return self.coordinator.data.get(key)
        if key not in current:
            return getattr(self.coordinator, key, None)
        if self.entity_description.native_unit_of_measurement is not None:
            default_value = 0
        else:
            default_value = None
        value = current.get(key, default_value)
        return value

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        key = self.entity_description.key
        data: dict[str, Any] = {}
        if key == "date":
            data["raw"] = self.coordinator.data.get("raw", None)
            return data
        if key not in ["trees", "grass", "weeds"]:
            return None
        pollen = self.coordinator.data.get("pollen", {})
        if not pollen:
            return None
        current = pollen[0]
        data["level"] = current[f"{key}_level"]
        data["details"] = current[f"{key}_details"]
        data["forecast"] = []
        for day_offset in range(1, len(pollen)):
            forecast_entry: dict[str, Any] = {}
            mapping = {
                key: "value",
                f"{key}_level": "level",
                f"{key}_details": "details",
            }
            for data_key in ["date", key, f"{key}_level", f"{key}_details"]:
                forecast_entry[mapping.get(data_key, data_key)] = pollen[day_offset][
                    data_key
                ]
            data["forecast"].append(forecast_entry)
        return data
