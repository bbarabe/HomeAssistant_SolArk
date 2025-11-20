"""Sensor platform for Sol-Ark Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, CONF_PLANT_ID, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sol-Ark Cloud sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    plant_id = entry.data[CONF_PLANT_ID]

    entities = []
    for sensor_type, sensor_info in SENSOR_TYPES.items():
        entities.append(
            SolArkCloudSensor(
                coordinator=coordinator,
                plant_id=plant_id,
                sensor_type=sensor_type,
                sensor_info=sensor_info,
                entry_id=entry.entry_id,
            )
        )

    async_add_entities(entities)


class SolArkCloudSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sol-Ark Cloud Sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        plant_id: str,
        sensor_type: str,
        sensor_info: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._plant_id = plant_id
        self._sensor_type = sensor_type
        self._sensor_info = sensor_info
        self._attr_name = f"Sol-Ark {sensor_info['name']}"
        self._attr_unique_id = f"{entry_id}_{sensor_type}"
        self._attr_icon = sensor_info["icon"]

        # Set unit of measurement
        if sensor_info["unit"] == "W":
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
        elif sensor_info["unit"] == "kWh":
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        elif sensor_info["unit"] == "%":
            self._attr_native_unit_of_measurement = PERCENTAGE
        else:
            self._attr_native_unit_of_measurement = sensor_info["unit"]

        # Set device class and state class
        self._attr_device_class = sensor_info.get("device_class")
        if sensor_info.get("state_class"):
            self._attr_state_class = SensorStateClass(sensor_info["state_class"])

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._plant_id)},
            name=f"Sol-Ark Plant {self._plant_id}",
            manufacturer="Sol-Ark",
            model="Sol-Ark Inverter",
            configuration_url="https://www.mysolark.com",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(self._sensor_type)
        
        # Handle special cases
        if self._sensor_type == "battery_power":
            # Positive = discharge, Negative = charge
            if value is not None:
                return float(value)
        
        return value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "plant_id": self._plant_id,
            "last_update": self.coordinator.last_update_success_time,
        }
        
        # Add helpful description for battery power
        if self._sensor_type == "battery_power" and self.native_value is not None:
            if self.native_value > 0:
                attrs["status"] = "discharging"
            elif self.native_value < 0:
                attrs["status"] = "charging"
            else:
                attrs["status"] = "idle"
        
        return attrs
