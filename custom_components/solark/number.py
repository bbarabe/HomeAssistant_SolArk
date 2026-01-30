"""SolArk configuration number entities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import asyncio
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE, DOMAIN


@dataclass
class SolArkNumberDescription(NumberEntityDescription):
    key: str


NUMBER_DESCRIPTIONS: list[SolArkNumberDescription] = [
    SolArkNumberDescription(
        key="sysWorkMode",
        name="System Work Mode",
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    SolArkNumberDescription(
        key="energyMode",
        name="Work Mode",
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    SolArkNumberDescription(
        key="solarMaxSellPower",
        name="Max Solar Power",
        native_unit_of_measurement="W",
        native_min_value=500,
        native_max_value=19500,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    SolArkNumberDescription(
        key="zeroExportPower",
        name="Zero Export Power",
        native_unit_of_measurement="W",
        native_min_value=0,
        native_max_value=500,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    SolArkNumberDescription(
        key="pvMaxLimit",
        name="Max Sell Power",
        native_unit_of_measurement="W",
        native_min_value=500,
        native_max_value=32000,
        native_step=1,
        mode=NumberMode.BOX,
    ),
]

for slot in range(1, 7):
    NUMBER_DESCRIPTIONS.append(
        SolArkNumberDescription(
            key=f"sellTime{slot}Pac",
            name=f"Power {slot}",
            native_unit_of_measurement="W",
            native_min_value=0,
            native_max_value=14000,
            native_step=1,
            mode=NumberMode.BOX,
        )
    )
    NUMBER_DESCRIPTIONS.append(
        SolArkNumberDescription(
            key=f"cap{slot}",
            name=f"Battery SOC {slot}",
            native_unit_of_measurement="%",
            native_min_value=0,
            native_max_value=100,
            native_step=1,
            mode=NumberMode.BOX,
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
    entities: list[SolArkSettingNumber] = [
        SolArkSettingNumber(coordinator, entry, api, desc)
        for desc in NUMBER_DESCRIPTIONS
    ]
    async_add_entities(entities, update_before_add=True)


class SolArkSettingNumber(CoordinatorEntity, NumberEntity):
    """Number entity for SolArk configuration."""

    entity_description: SolArkNumberDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        api,
        description: SolArkNumberDescription,
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
        self._pending_value: float | None = None
        self._pending_until = None

    @property
    def native_value(self) -> float | None:
        settings = (self.coordinator.data or {}).get("settings") or {}
        value = settings.get(self.entity_description.key)
        if value is None:
            return None
        try:
            current = float(value)
        except (TypeError, ValueError):
            current = None
        return self._apply_pending(current)

    async def async_set_native_value(self, value: float) -> None:
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

        payload_value: Any
        if self.entity_description.key.startswith("cap") or self.entity_description.key.endswith(
            "Pac"
        ):
            payload_value = int(value)
        else:
            payload_value = int(value) if value.is_integer() else value

        await self._api.set_common_settings(
            sn=sn,
            updates={self.entity_description.key: payload_value},
            require_master=True,
        )
        self._set_pending_value(float(value))
        self.hass.async_create_task(self._refresh_after_delay())
        await self.coordinator.async_request_refresh()

    async def _handle_write_blocked(self) -> None:
        """Force a refresh so the UI reverts to the current value."""
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    def _set_pending_value(self, value: float) -> None:
        self._pending_value = value
        self._pending_until = dt_util.utcnow() + timedelta(seconds=30)

    def _apply_pending(self, current: float | None) -> float | None:
        if self._pending_value is None or self._pending_until is None:
            return current
        if dt_util.utcnow() > self._pending_until:
            self._pending_value = None
            self._pending_until = None
            return current
        if current is not None and abs(current - self._pending_value) < 0.001:
            self._pending_value = None
            self._pending_until = None
            return current
        return self._pending_value

    async def _refresh_after_delay(self) -> None:
        await asyncio.sleep(3)
        await self.coordinator.async_request_refresh()
