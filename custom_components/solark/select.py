"""SolArk configuration select entities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import asyncio
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE, DOMAIN


@dataclass
class SolArkSelectDescription(SelectEntityDescription):
    key: str
    options_map: dict[str, int]


SELECT_DESCRIPTIONS: list[SolArkSelectDescription] = [
    SolArkSelectDescription(
        key="sysWorkMode",
        name="Work Mode",
        options_map={
            "Grid Selling": 0,
            "Limited power to Load": 1,
            "Limited to Home": 2,
        },
    ),
    SolArkSelectDescription(
        key="energyMode",
        name="Energy Pattern",
        options_map={
            "Batt First": 0,
            "Load First": 1,
        },
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data["settings_coordinator"]
    api = data["api"]

    entities: list[SolArkSettingSelect] = [
        SolArkSettingSelect(coordinator, entry, api, desc)
        for desc in SELECT_DESCRIPTIONS
    ]
    async_add_entities(entities, update_before_add=True)


class SolArkSettingSelect(CoordinatorEntity, SelectEntity):
    """Select entity for SolArk configuration."""

    entity_description: SolArkSelectDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        api,
        description: SolArkSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = list(description.options_map.keys())
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }
        self._pending_value: str | None = None
        self._pending_until = None

    @property
    def current_option(self) -> str | None:
        settings = (self.coordinator.data or {}).get("settings") or {}
        value = settings.get(self.entity_description.key)
        try:
            current_value = int(value)
        except (TypeError, ValueError):
            current_value = None
        current = None
        if current_value is not None:
            for label, mapped in self.entity_description.options_map.items():
                if mapped == current_value:
                    current = label
                    break
        return self._apply_pending(current)

    async def async_select_option(self, option: str) -> None:
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

        if option not in self.entity_description.options_map:
            raise HomeAssistantError(f"Invalid option: {option}")

        await self._api.set_common_settings(
            sn=sn,
            updates={self.entity_description.key: self.entity_description.options_map[option]},
            require_master=True,
        )
        self._set_pending_value(option)
        self.hass.async_create_task(self._refresh_after_delay())
        await self.coordinator.async_request_refresh()

    async def _handle_write_blocked(self) -> None:
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    def _set_pending_value(self, value: str) -> None:
        self._pending_value = value
        self._pending_until = dt_util.utcnow() + timedelta(seconds=30)

    def _apply_pending(self, current: str | None) -> str | None:
        if self._pending_value is None or self._pending_until is None:
            return current
        if dt_util.utcnow() > self._pending_until:
            self._pending_value = None
            self._pending_until = None
            return current
        if current == self._pending_value:
            self._pending_value = None
            self._pending_until = None
            return current
        return self._pending_value

    async def _refresh_after_delay(self) -> None:
        await asyncio.sleep(3)
        await self.coordinator.async_request_refresh()
