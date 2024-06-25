import logging

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.typing import StateType
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)

from .coordinator import PollenDataUpdateCoordinator
from .const import DOMAIN as SENSOR_DOMAIN, NAME

_LOGGER: logging.Logger = logging.getLogger(__package__)


def get_sensor_descriptions() -> list[SensorEntityDescription]:  # type: ignore
    descriptions: list[SensorEntityDescription] = [
        SensorEntityDescription(
            key="trees",
            translation_key="trees",
            icon="mdi:tree",
            state_class="measurement",
            native_unit_of_measurement="ppm",
        ),
        SensorEntityDescription(
            key="grass",
            translation_key="grass",
            icon="mdi:grass",
            state_class="measurement",
            native_unit_of_measurement="ppm",
        ),
        SensorEntityDescription(
            key="weeds",
            translation_key="weeds",
            icon="mdi:cannabis",
            state_class="measurement",
            native_unit_of_measurement="ppm",
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
            entity_registry_enabled_default=False
        ),
        SensorEntityDescription(
            key="longitude",
            translation_key="longitude",
            icon="mdi:longitude",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False
        ),
        SensorEntityDescription(
            key="region",
            translation_key="region",
            icon="mdi:earth",
            device_class=SensorDeviceClass.ENUM,
            entity_category=EntityCategory.DIAGNOSTIC,
            options=[
                "fr",
                "it",
                "nl",
                "uk",
                "us"
            ],
            entity_registry_enabled_default=False
        ),
    ]
    return descriptions


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PollenDataUpdateCoordinator = hass.data[SENSOR_DOMAIN][entry.entry_id]
    entities: list[KleenexSensor] = []

    for description in get_sensor_descriptions():
        entities.append(
            KleenexSensor(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                description=description,
            )
        )
    async_add_entities(entities)


class KleenexSensor(CoordinatorEntity[PollenDataUpdateCoordinator], SensorEntity):

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PollenDataUpdateCoordinator,
        entry_id: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}-{NAME}" f"{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        key = self.entity_description.key
        _LOGGER.debug(f"{self.coordinator.data[0]}")
        data = self.coordinator.data[0]
        if key not in data:
            return getattr(self.coordinator, key)
        pollen_info = data[key]
        if self.entity_description.native_unit_of_measurement is not None:
            default_value = 0
        else:
            default_value = "-"
        return int(pollen_info.get("pollen", default_value))  # type: ignore

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        key = self.entity_description.key
        if key not in self.coordinator.data[0]:
            return None
        MAPPINGS: dict[str, dict[str, Any]] = {
            "value": {"data": "pollen", "func": int},
            "level": {"data": "level"},
            "details": {"data": "details"},
        }
        data: dict[str, dict[str, Any] | list[Any]] = {}
        data["current"] = {
            "date": self.coordinator.data[0]["date"],
            "level": self.coordinator.data[0][key]["level"],
            "details": self.coordinator.data[0][key]["details"],
        }
        data["forecast"] = []
        for offset in range(1, 5):
            forecast_entry: dict[str, Any] = {}
            forecast_entry["date"] = self.coordinator.data[offset]["date"]
            for mapping_key, mapping in MAPPINGS.items():
                # mapping = MAPPINGS[mapping_key]
                forecast_entry[mapping_key] = self.coordinator.data[offset][key][
                    mapping.get("data")
                ]
                if "func" in mapping:
                    forecast_entry[mapping_key] = mapping["func"](
                        forecast_entry[mapping_key]
                    )  # type: ignore
            data["forecast"].append(forecast_entry)
        return data
