"""SolArk configuration select entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE, DOMAIN


@dataclass
class SolArkSelectDescription(SelectEntityDescription):
    key: str
    options_map: dict[str, int] = field(default_factory=dict)


@dataclass
class SolArkSlotModeDescription(SelectEntityDescription):
    key: str
    slot: int = 0


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

SLOT_MODE_DESCRIPTIONS: list[SolArkSlotModeDescription] = [
    SolArkSlotModeDescription(
        key=f"time{slot}mode",
        name=f"Slot {slot} - Mode",
        slot=slot,
        options=["Sell", "Charge"],
    )
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

    entities: list[SelectEntity] = [
        SolArkSettingSelect(coordinator, entry, api, desc)
        for desc in SELECT_DESCRIPTIONS
    ]
    entities.extend(
        SolArkSlotModeSelect(coordinator, entry, api, desc)
        for desc in SLOT_MODE_DESCRIPTIONS
    )
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
        return current

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
        refresh_burst = self.hass.data[DOMAIN][self._entry_id].get(
            "settings_refresh_burst"
        )
        if refresh_burst:
            await refresh_burst()
        await self.coordinator.async_request_refresh()

    async def _handle_write_blocked(self) -> None:
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()


class SolArkSlotModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for per-slot sell/charge mode."""

    entity_description: SolArkSlotModeDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        api,
        description: SolArkSlotModeDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = list(description.options)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }

    @property
    def current_option(self) -> str | None:
        settings = (self.coordinator.data or {}).get("settings") or {}
        slot = self.entity_description.slot
        sell_value = settings.get(f"genTime{slot}on")
        charge_value = settings.get(f"time{slot}on")
        if sell_value is None or charge_value is None:
            return None
        sell_on = self._coerce_bool(sell_value)
        charge_on = self._coerce_bool(charge_value)
        if sell_on and not charge_on:
            return "Sell"
        if charge_on and not sell_on:
            return "Charge"
        return None

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

        if option not in self._attr_options:
            raise HomeAssistantError(f"Invalid option: {option}")

        slot = self.entity_description.slot
        sell_mode = option == "Sell"
        updates = {
            f"genTime{slot}on": sell_mode,
            f"time{slot}on": not sell_mode,
        }
        await self._api.set_common_settings(
            sn=sn,
            updates=updates,
            require_master=True,
        )
        refresh_burst = self.hass.data[DOMAIN][self._entry_id].get(
            "settings_refresh_burst"
        )
        if refresh_burst:
            await refresh_burst()
        await self.coordinator.async_request_refresh()

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        try:
            return bool(int(value))
        except (TypeError, ValueError):
            return bool(value)
