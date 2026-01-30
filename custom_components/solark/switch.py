"""SolArk configuration switches."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE, DOMAIN


@dataclass
class SolArkSwitchDescription(SwitchEntityDescription):
    key: str
    on_value: Any = True
    off_value: Any = False


@dataclass
class SolArkSlotModeDescription(SwitchEntityDescription):
    key: str
    slot: int = 0


SWITCH_DESCRIPTIONS: list[SolArkSwitchDescription] = [
    SolArkSwitchDescription(
        key="solarSell",
        name="Solar Sell",
        on_value=1,
        off_value=0,
    ),
    SolArkSwitchDescription(
        key="peakAndVallery",
        name="Energy Pattern (Time Of Use)",
        on_value=1,
        off_value=0,
    ),
]

SLOT_MODE_DESCRIPTIONS: list[SolArkSlotModeDescription] = []
for slot in range(1, 7):
    SLOT_MODE_DESCRIPTIONS.append(
        SolArkSlotModeDescription(
            key=f"time{slot}mode",
            name=f"Time {slot} Mode (Sell/Charge)",
            slot=slot,
        )
    )

for day_key, day_label in (
    ("mondayOn", "Monday"),
    ("tuesdayOn", "Tuesday"),
    ("wednesdayOn", "Wednesday"),
    ("thursdayOn", "Thursday"),
    ("fridayOn", "Friday"),
    ("saturdayOn", "Saturday"),
    ("sundayOn", "Sunday"),
):
    SWITCH_DESCRIPTIONS.append(
        SolArkSwitchDescription(
            key=day_key,
            name=f"Time Of Use {day_label}",
            on_value=True,
            off_value=False,
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data["settings_coordinator"]
    api = data["api"]
    entities: list[SwitchEntity] = [
        SolArkSettingSwitch(coordinator, entry, api, desc)
        for desc in SWITCH_DESCRIPTIONS
    ]
    entities.extend(
        SolArkSlotModeSwitch(coordinator, entry, api, desc)
        for desc in SLOT_MODE_DESCRIPTIONS
    )
    async_add_entities(entities, update_before_add=True)


class SolArkSettingSwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for SolArk configuration."""

    entity_description: SolArkSwitchDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        api,
        description: SolArkSwitchDescription,
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
    def is_on(self) -> bool | None:
        settings = (self.coordinator.data or {}).get("settings") or {}
        value = settings.get(self.entity_description.key)
        if value is None:
            return None
        if value == self.entity_description.on_value:
            return True
        elif value == self.entity_description.off_value:
            return False
        else:
            return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_value(self.entity_description.on_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_value(self.entity_description.off_value)

    async def _async_set_value(self, value: Any) -> None:
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

        await self._api.set_common_settings(
            sn=sn,
            updates={self.entity_description.key: value},
            require_master=True,
        )
        await self.coordinator.async_request_refresh()

    async def _handle_write_blocked(self) -> None:
        """Force a refresh so the UI reverts to the current value."""
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()


class SolArkSlotModeSwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for per-slot sell/charge mode."""

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
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }

    @property
    def is_on(self) -> bool | None:
        settings = (self.coordinator.data or {}).get("settings") or {}
        slot = self.entity_description.slot
        sell_value = settings.get(f"genTime{slot}on")
        charge_value = settings.get(f"time{slot}on")
        return self._derive_mode(sell_value, charge_value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_mode(False)

    async def _async_set_mode(self, sell_mode: bool) -> None:
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

        slot = self.entity_description.slot
        updates = {
            f"genTime{slot}on": sell_mode,
            f"time{slot}on": not sell_mode,
        }
        await self._api.set_common_settings(
            sn=sn,
            updates=updates,
            require_master=True,
        )
        await self.coordinator.async_request_refresh()

    def _derive_mode(self, sell_value: Any, charge_value: Any) -> bool | None:
        if sell_value is None or charge_value is None:
            return None
        sell_on = self._coerce_bool(sell_value)
        charge_on = self._coerce_bool(charge_value)
        if sell_on and not charge_on:
            return True
        if charge_on and not sell_on:
            return False
        return None

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        try:
            return bool(int(value))
        except (TypeError, ValueError):
            return bool(value)

    async def _handle_write_blocked(self) -> None:
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
