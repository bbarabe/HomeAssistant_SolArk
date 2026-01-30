"""SolArk configuration time entities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time as dt_time
from typing import Any

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE, DOMAIN


@dataclass
class SolArkTimeDescription(TimeEntityDescription):
    key: str


TIME_DESCRIPTIONS: list[SolArkTimeDescription] = [
    SolArkTimeDescription(key=f"sellTime{slot}", name=f"Time {slot}")
    for slot in range(1, 7)
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data["settings_coordinator"]
    api = data["api"]
    entities: list[SolArkSettingTime] = [
        SolArkSettingTime(coordinator, entry, api, desc)
        for desc in TIME_DESCRIPTIONS
    ]
    async_add_entities(entities, update_before_add=True)


class SolArkSettingTime(CoordinatorEntity, TimeEntity):
    """Time entity for SolArk configuration."""

    entity_description: SolArkTimeDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        api,
        description: SolArkTimeDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }

    @property
    def native_value(self) -> dt_time | None:
        settings = (self.coordinator.data or {}).get("settings") or {}
        value = settings.get(self.entity_description.key)
        if not value:
            return None
        if isinstance(value, dt_time):
            return value
        if isinstance(value, str) and ":" in value:
            try:
                hour_str, minute_str = value.split(":", 1)
                return dt_time(int(hour_str), int(minute_str))
            except ValueError:
                return None
        return None

    async def async_set_value(self, value: dt_time) -> None:
        allow_write = bool(
            self.hass.data[DOMAIN][self._entry_id].get(
                "allow_write_access", DEFAULT_ALLOW_WRITE
            )
        )
        if not allow_write:
            await self._handle_write_blocked()
            raise HomeAssistantError("Write access is disabled for SolArk.")

        data = self.coordinator.data or {}
        sn = data.get("sn")
        if not sn:
            raise HomeAssistantError("Master inverter not available.")

        payload_value = value.strftime("%H:%M")
        await self._api.set_common_settings(
            sn=sn,
            updates={self.entity_description.key: payload_value},
            require_master=True,
        )
        await self.coordinator.async_request_refresh()

    async def _handle_write_blocked(self) -> None:
        """Force a refresh so the UI reverts to the current value."""
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
