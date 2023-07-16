import logging

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from .coordinator import PollenDataUpdateCoordinator
from .const import DOMAIN, NAME, MODEL, MANUFACTURER

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    coordinator: PollenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    INSTRUMENTS = [
        ("trees", "Tree Pollen", "trees", "mdi:tree", None, None),
        ("grass", "Grass Pollen", "grass", "mdi:grass", None, None),
        ("weeds", "Weed Pollen", "weeds", "mdi:cannabis", None, None),
        (
            "last_updated_pollen",
            "Last Updated (Pollen)",
            "",
            "mdi:clock-outline",
            None,
            EntityCategory.DIAGNOSTIC,
        ),
    ]

    sensors = [
        KleenexSensor(
            coordinator,
            entry,
            id,
            description,
            key,
            icon,
            device_class,
            entity_category,
        )
        for id, description, key, icon, device_class, entity_category in INSTRUMENTS
    ]

    async_add_devices(sensors, True)


class KleenexSensor(CoordinatorEntity[PollenDataUpdateCoordinator]):
    def __init__(
        self,
        coordinator: PollenDataUpdateCoordinator,
        entry: ConfigEntry,
        id: str,
        description: str,
        key: str,
        icon: str,
        device_class: str | None,
        entity_category: ConfigEntry | None,
    ) -> None:
        super().__init__(coordinator)
        self._id = id
        self.description = description
        self.key = key
        self._icon = icon
        self._device_class: str | None = device_class
        self._entry: ConfigEntry = entry
        self._attr_entity_category: ConfigEntry = entity_category

    @property
    def state(self) -> str:
        if self.key != "":
            return self.coordinator.data[0][self.key]["pollen"]
        else:
            return self.coordinator.last_updated

    @property
    def unit_of_measurement(self) -> str:
        if self.key != "":
            return self.coordinator.data[0][self.key]["unit_of_measure"]

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def device_class(self) -> str:
        return self._device_class

    @property
    def name(self) -> str:
        return f"{self.description} ({self._entry.data['name']})"

    @property
    def id(self) -> str:
        return f"{DOMAIN}_{self._id}"

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}-{self._id}-{self._entry.data['name']}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.api.position)},
            "name": f"{NAME} ({self._entry.data['name']})",
            "model": MODEL,
            "manufacturer": MANUFACTURER,
        }

    @property
    def available(self) -> bool:
        return not not self.coordinator.data

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        MAPPINGS: dict[str, dict[str, Any]] = {
            "value": {"data": "pollen", "func": int},
            "level": {"data": "level"},
            "details": {"data": "details"},
        }
        data: dict[str, dict[str, Any] | list[Any]] = {}
        if self.key != "":  # trees, weeds, grass
            data["current"] = {
                "date": self.coordinator.data[0]["date"],
                "level": self.coordinator.data[0][self.key]["level"],
                "details": self.coordinator.data[0][self.key]["details"],
            }
            data["forecast"] = []
            for offset in range(1, 5):
                forecast_entry: dict[str, Any] = {}
                forecast_entry["date"] = self.coordinator.data[offset]["date"]
                for mapping_key in MAPPINGS:
                    mapping = MAPPINGS[mapping_key]
                    forecast_entry[mapping_key] = self.coordinator.data[offset][
                        self.key
                    ][mapping.get("data")]
                    if "func" in mapping:
                        forecast_entry[mapping_key] = mapping["func"](
                            forecast_entry[mapping_key]
                        )
                data["forecast"].append(forecast_entry)
        return data
