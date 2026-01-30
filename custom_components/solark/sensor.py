"""SolArk sensors (high-value set using energy/flow)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import inspect
from typing import Any, Iterable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN


@dataclass
class SolArkSensorDescription(SensorEntityDescription):
    key: str


@dataclass
class SolArkIntegratedEnergyDescription(SensorEntityDescription):
    key: str
    source_key: str


SENSOR_DESCRIPTIONS: list[SolArkSensorDescription] = [
    # Real-time powers from energy/flow:
    SolArkSensorDescription(
        key="pv_power",
        name="PV Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolArkSensorDescription(
        key="battery_power",
        name="Battery Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolArkSensorDescription(
        key="battery_charge_power",
        name="Battery Charge Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolArkSensorDescription(
        key="battery_discharge_power",
        name="Battery Discharge Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolArkSensorDescription(
        key="grid_power",
        name="Grid Power (Net)",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolArkSensorDescription(
        key="load_power",
        name="Load Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Grid import/export derived from meterA/B/C:
    SolArkSensorDescription(
        key="grid_import_power",
        name="Grid Import Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SolArkSensorDescription(
        key="grid_export_power",
        name="Grid Export Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Battery SOC:
    SolArkSensorDescription(
        key="battery_soc",
        name="Battery SOC",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Energy sensors (for Energy dashboard):
    SolArkSensorDescription(
        key="energy_today",
        name="Energy Today",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SolArkSensorDescription(
        key="energy_total",
        name="Energy Total",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Status sensors:
    SolArkSensorDescription(
        key="grid_status",
        name="Grid Status",
        device_class=SensorDeviceClass.ENUM,
        options=["Active", "Inactive", "Unknown"],
    ),
    SolArkSensorDescription(
        key="generator_status",
        name="Generator Status",
        device_class=SensorDeviceClass.ENUM,
        options=["Running", "Off", "Unknown"],
    ),
]

INTEGRATED_ENERGY_DESCRIPTIONS: list[SolArkIntegratedEnergyDescription] = [
    SolArkIntegratedEnergyDescription(
        key="grid_import_energy",
        source_key="grid_import_power",
        name="Grid Import Energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SolArkIntegratedEnergyDescription(
        key="grid_export_energy",
        source_key="grid_export_power",
        name="Grid Export Energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SolArkIntegratedEnergyDescription(
        key="battery_charge_energy",
        source_key="battery_charge_power",
        name="Battery Charge Energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SolArkIntegratedEnergyDescription(
        key="battery_discharge_energy",
        source_key="battery_discharge_power",
        name="Battery Discharge Energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
]

try:
    from homeassistant.components.integration.sensor import (
        IntegrationSensor,
        IntegrationMethod,
    )

    HAS_INTEGRATION_SENSOR = True
except Exception:  # pragma: no cover - handled at runtime in HA
    IntegrationSensor = None  # type: ignore[assignment]
    IntegrationMethod = None  # type: ignore[assignment]
    HAS_INTEGRATION_SENSOR = False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolArk sensors from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data["coordinator"]

    entities: list[SensorEntity] = [
        SolArkSensor(coordinator, entry, desc) for desc in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities, update_before_add=True)

    energy_entities = _build_energy_entities(hass, entry, coordinator)
    if energy_entities:
        async_add_entities(energy_entities, update_before_add=True)


class SolArkSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SolArk sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SolArkSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        return data.get(self.entity_description.key)


class SolArkIntegratedEnergySensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """Integrate a power sensor into a total energy sensor (kWh)."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SolArkIntegratedEnergyDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }
        self._energy_kwh: float | None = None
        self._last_power: float | None = None
        self._last_update: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore last known energy value."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._energy_kwh = float(last_state.state)
            except (TypeError, ValueError):
                self._energy_kwh = 0.0
        else:
            self._energy_kwh = 0.0

    @property
    def native_value(self) -> Any:
        return self._energy_kwh

    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data or {}
        power = data.get(self.entity_description.source_key)
        try:
            power_w = float(power) if power is not None else 0.0
        except (TypeError, ValueError):
            power_w = 0.0
        if power_w < 0.0:
            power_w = 0.0

        now = dt_util.utcnow()
        if self._last_update is None:
            self._last_update = now
            self._last_power = power_w
            super()._handle_coordinator_update()
            return

        delta_s = (now - self._last_update).total_seconds()
        if delta_s > 0:
            last_power = self._last_power if self._last_power is not None else power_w
            avg_power = (last_power + power_w) / 2.0
            if avg_power < 0.0:
                avg_power = 0.0
            increment_kwh = (avg_power * delta_s) / 3600.0 / 1000.0
            if increment_kwh < 0.0:
                increment_kwh = 0.0
            if self._energy_kwh is None:
                self._energy_kwh = 0.0
            self._energy_kwh += increment_kwh

        self._last_update = now
        self._last_power = power_w
        super()._handle_coordinator_update()


def _build_energy_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: DataUpdateCoordinator,
) -> list[SensorEntity]:
    if not INTEGRATED_ENERGY_DESCRIPTIONS:
        return []

    if HAS_INTEGRATION_SENSOR:
        registry = er.async_get(hass)
        device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }
        return [
            _create_integration_sensor(
                hass=hass,
                registry=registry,
                entry=entry,
                description=desc,
                device_info=device_info,
            )
            for desc in INTEGRATED_ENERGY_DESCRIPTIONS
        ]

    return [
        SolArkIntegratedEnergySensor(coordinator, entry, desc)
        for desc in INTEGRATED_ENERGY_DESCRIPTIONS
    ]


def _create_integration_sensor(
    hass: HomeAssistant,
    registry: er.EntityRegistry,
    entry: ConfigEntry,
    description: SolArkIntegratedEnergyDescription,
    device_info: dict[str, Any],
) -> SensorEntity:
    source_unique_id = f"{entry.entry_id}_{description.source_key}"
    source_entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, source_unique_id
    ) or f"sensor.solark_{description.source_key}"

    name = description.name or description.key
    unique_id = f"{entry.entry_id}_{description.key}"
    integration_method = _resolve_integration_method()
    kwargs = _build_integration_kwargs(
        hass=hass,
        source_entity_id=source_entity_id,
        name=name,
        unique_id=unique_id,
        integration_method=integration_method,
    )

    sensor = IntegrationSensor(**kwargs)  # type: ignore[operator]
    sensor._attr_device_info = device_info
    sensor._attr_has_entity_name = True
    if not getattr(sensor, "unique_id", None):
        sensor._attr_unique_id = unique_id
    if getattr(sensor, "device_class", None) is None:
        sensor._attr_device_class = SensorDeviceClass.ENERGY
    if getattr(sensor, "state_class", None) is None:
        sensor._attr_state_class = SensorStateClass.TOTAL_INCREASING
    return sensor


def _build_integration_kwargs(
    *,
    hass: HomeAssistant,
    source_entity_id: str,
    name: str,
    unique_id: str,
    integration_method: Any,
) -> dict[str, Any]:
    params = inspect.signature(IntegrationSensor.__init__).parameters  # type: ignore[union-attr]
    kwargs: dict[str, Any] = {}

    _set_if_present(params, kwargs, "hass", hass)
    _set_if_present(
        params,
        kwargs,
        ("source_entity_id", "source_entity", "source"),
        source_entity_id,
    )
    _set_if_present(params, kwargs, "name", name)
    _set_if_present(params, kwargs, ("round_digits", "round"), 3)
    _set_if_present(params, kwargs, "unit_prefix", "k")
    _set_if_present(params, kwargs, "unit_time", "h")
    _set_if_present(params, kwargs, ("integration_method", "method"), integration_method)
    _set_if_present(params, kwargs, "unique_id", unique_id)
    _set_if_present(params, kwargs, "unit_of_measurement", "kWh")

    return kwargs


def _set_if_present(
    params: Iterable[str],
    kwargs: dict[str, Any],
    keys: str | tuple[str, ...],
    value: Any,
) -> None:
    if isinstance(keys, str):
        keys = (keys,)
    for key in keys:
        if key in params:
            kwargs[key] = value
            return


def _resolve_integration_method() -> Any:
    if IntegrationMethod is None:
        return "trapezoidal"
    return getattr(IntegrationMethod, "TRAPEZOIDAL", "trapezoidal")
