"""Sensor platform for the Pollenradar integration."""

import logging

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)
from .coordinator import PollenDataUpdateCoordinator
from .const import DOMAIN, NAME, MODEL, MANUFACTURER, CONF_NAME

_LOGGER: logging.Logger = logging.getLogger(__package__)


@dataclass(kw_only=True, frozen=True)
class KleenexDetailSensorEntityDescription(SensorEntityDescription):
    """Describes Kleenex detail sensor entity."""

    group: str | None = None
    pollen_type: str | None = None


def get_sensor_descriptions() -> list[SensorEntityDescription]:
    """Return a list of sensor descriptions."""
    level_options = ["low", "moderate", "high", "very-high"]
    descriptions: list[SensorEntityDescription] = [
        *[
            SensorEntityDescription(
                key=key,
                translation_key=key,
                icon=icon,
                state_class="measurement",
                native_unit_of_measurement="ppm",
            )
            for key, icon in [
                ("trees", "mdi:tree-outline"),
                ("grass", "mdi:grass"),
                ("weeds", "mdi:flower-pollen"),
            ]
        ],
        *[
            SensorEntityDescription(
                key=key,
                translation_key=key,
                device_class=SensorDeviceClass.ENUM,
                options=level_options,
            )
            for key in ["trees_level", "grass_level", "weeds_level"]
        ],
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


def get_detail_sensor_descriptions(
    pollen: list[dict[str, Any]],
) -> list[KleenexDetailSensorEntityDescription]:
    """Return a list of detail sensor descriptions."""
    descriptions: list[KleenexDetailSensorEntityDescription] = []
    for group, icon in [
        ("trees_details", "mdi:tree-outline"),
        ("grass_details", "mdi:grass"),
        ("weeds_details", "mdi:flower-pollen"),
    ]:
        for details in pollen[0].get(group, []):
            descriptions.append(
                KleenexDetailSensorEntityDescription(
                    key="value",
                    pollen_type=details["name"],
                    translation_key="detail_value",
                    translation_placeholders={"name": details["name"]},
                    group=group,
                    icon=icon,
                    state_class="measurement",
                    native_unit_of_measurement="ppm",
                    entity_registry_enabled_default=False,
                )
            )
            descriptions.append(
                KleenexDetailSensorEntityDescription(
                    key="level",
                    pollen_type=details["name"],
                    translation_key="detail_level",
                    translation_placeholders={"name": details["name"]},
                    group=group,
                    device_class=SensorDeviceClass.ENUM,
                    options=["low", "moderate", "high", "very-high"],
                    entity_registry_enabled_default=False,
                ),
            )
    return descriptions


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: PollenDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    pollen = coordinator.data.get("pollen", {})

    latitude = config_entry.data.get(CONF_LATITUDE)
    longitude = config_entry.data.get(CONF_LONGITUDE)
    name = config_entry.data.get(CONF_NAME)

    device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, f"{latitude}x{longitude}")},
        name=f"{NAME} ({name})",
        model=MODEL,
        manufacturer=MANUFACTURER,
    )

    for description in get_sensor_descriptions():
        entities.append(
            KleenexSensor(
                coordinator=coordinator,
                entry_id=config_entry.entry_id,
                description=description,
                config_entry=config_entry,
                device_info=device_info,
            )
        )
    for description in get_detail_sensor_descriptions(pollen):
        entities.append(
            KleenexDetailSensor(
                coordinator=coordinator,
                entry_id=config_entry.entry_id,
                description=description,
                config_entry=config_entry,
                device_info=device_info,
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
        config_entry: ConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{entry_id}-{NAME}{description.key}"
        self._attr_device_info = device_info
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        key = self.entity_description.key
        pollen = self.coordinator.data.get("pollen", {})
        current = pollen[0] if pollen else {}
        if key in current:
            return current.get(key, None)
        if self.coordinator.data.get(key, None) is not None:
            return self.coordinator.data.get(key)
        return self._config_entry.data.get(key, None)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes of the sensor."""
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


class KleenexDetailSensor(CoordinatorEntity[PollenDataUpdateCoordinator], SensorEntity):
    """Representation of a detail sensor."""

    _attr_has_entity_name = True

    entity_description: KleenexDetailSensorEntityDescription

    def __init__(
        self,
        coordinator: PollenDataUpdateCoordinator,
        entry_id: str,
        description: KleenexDetailSensorEntityDescription,
        config_entry: ConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{entry_id}-{NAME}{description.group}-{description.pollen_type}-{description.key}"
        self._attr_device_info = device_info
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the state of the detail sensor."""
        pollen = self.coordinator.data.get("pollen", {})
        if not pollen:
            return None
        key = self.entity_description.key
        pollen_type = self.entity_description.pollen_type
        group = self.entity_description.group
        return self.__get_detail_value(pollen, 0, group, pollen_type, key)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes of the detail sensor."""
        pollen = self.coordinator.data.get("pollen", {})
        if not pollen:
            return None
        data: dict[str, Any] = {}
        key = self.entity_description.key
        pollen_type = self.entity_description.pollen_type
        group = self.entity_description.group
        data["forecast"] = []
        for day_offset in range(1, len(pollen)):
            data["forecast"].append(
                {
                    "date": pollen[day_offset]["date"],
                    key: self.__get_detail_value(
                        pollen, day_offset, group, pollen_type, key
                    ),
                }
            )
        return data

    def __get_detail_value(
        self,
        pollen: list[dict[str, Any]],
        day_offset: int,
        group: str | None,
        pollen_type: str | None,
        key: str,
    ) -> Any:
        details = pollen[day_offset].get(group, []) if group else []
        detail = [item for item in details if item["name"] == pollen_type]
        if not detail:
            return None
        value = detail[0].get(key, None)
        return value
