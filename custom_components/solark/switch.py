"""SolArk configuration switches."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import asyncio
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE, DOMAIN


@dataclass
class SolArkSwitchDescription(SwitchEntityDescription):
    key: str
    on_value: Any = True
    off_value: Any = False


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

for slot in range(1, 7):
    SWITCH_DESCRIPTIONS.append(
        SolArkSwitchDescription(
            key=f"time{slot}on",
            name=f"Sell Time {slot} Enabled",
            on_value=True,
            off_value=False,
        )
    )
    SWITCH_DESCRIPTIONS.append(
        SolArkSwitchDescription(
            key=f"genTime{slot}on",
            name=f"Charge Time {slot} Enabled",
            on_value=True,
            off_value=False,
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
    entities: list[SolArkSettingSwitch] = [
        SolArkSettingSwitch(coordinator, entry, api, desc)
        for desc in SWITCH_DESCRIPTIONS
    ]
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
        self._pending_value: bool | None = None
        self._pending_until = None

    @property
    def is_on(self) -> bool | None:
        settings = (self.coordinator.data or {}).get("settings") or {}
        value = settings.get(self.entity_description.key)
        if value is None:
            return None
        if value == self.entity_description.on_value:
            current = True
        elif value == self.entity_description.off_value:
            current = False
        else:
            current = bool(value)
        return self._apply_pending(current)

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
        self._set_pending_value(value == self.entity_description.on_value)
        self.hass.async_create_task(self._refresh_after_delay())
        await self.coordinator.async_request_refresh()

    async def _handle_write_blocked(self) -> None:
        """Force a refresh so the UI reverts to the current value."""
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    def _set_pending_value(self, value: bool) -> None:
        self._pending_value = value
        self._pending_until = dt_util.utcnow() + timedelta(seconds=30)

    def _apply_pending(self, current: bool | None) -> bool | None:
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
