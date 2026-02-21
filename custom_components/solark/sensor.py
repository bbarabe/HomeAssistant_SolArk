"""SolArk sensors (high-value set using energy/flow)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import asyncio
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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .services import (
    WORK_MODE_REVERSE,
    ENERGY_MODE_REVERSE,
    slot_mode_from_api,
)
from .solark_logging import get_logger

_LOGGER = get_logger(__name__)


@dataclass
class SolArkSensorDescription(SensorEntityDescription):
    key: str


@dataclass
class SolArkIntegratedEnergyDescription(SensorEntityDescription):
    key: str
    source_key: str = field(default="")


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
    SolArkSensorDescription(
        key="ac_relay_status",
        name="AC Relay Status",
        device_class=SensorDeviceClass.ENUM,
        options=["Connected", "Disconnected", "Unknown"],
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
    SolArkIntegratedEnergyDescription(
        key="home_consumption_energy",
        source_key="load_power",
        name="Home Consumption Energy",
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


# Configuration sensors (read-only, from settings coordinator)
@dataclass
class SolArkConfigSensorDescription(SensorEntityDescription):
    """Description for config sensors."""

    key: str
    api_key: str = ""
    value_fn: Any = None  # Optional transform function


def _bool_to_str(val: Any) -> str:
    """Convert bool/int to On/Off string."""
    if val is None:
        return "Unknown"
    if isinstance(val, bool):
        return "On" if val else "Off"
    try:
        return "On" if int(val) else "Off"
    except (TypeError, ValueError):
        return "Unknown"


def _work_mode_to_str(val: Any) -> str:
    """Convert work mode int to string."""
    if val is None:
        return "Unknown"
    try:
        return WORK_MODE_REVERSE.get(int(val), f"Unknown ({val})")
    except (TypeError, ValueError):
        return "Unknown"


def _energy_mode_to_str(val: Any) -> str:
    """Convert energy mode int to string."""
    if val is None:
        return "Unknown"
    try:
        return ENERGY_MODE_REVERSE.get(int(val), f"Unknown ({val})")
    except (TypeError, ValueError):
        return "Unknown"


def _coerce_bool(value: Any) -> bool:
    """Coerce value to boolean."""
    if isinstance(value, bool):
        return value
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return bool(value)


CONFIG_SENSOR_DESCRIPTIONS: list[SolArkConfigSensorDescription] = [
    # Power limits
    SolArkConfigSensorDescription(
        key="config_max_solar_power",
        api_key="solarMaxSellPower",
        name="Max Solar Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
    ),
    SolArkConfigSensorDescription(
        key="config_zero_export_power",
        api_key="zeroExportPower",
        name="Zero Export Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
    ),
    SolArkConfigSensorDescription(
        key="config_max_sell_power",
        api_key="pvMaxLimit",
        name="Max Sell Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
    ),
    # Boolean settings
    SolArkConfigSensorDescription(
        key="config_solar_sell",
        api_key="solarSell",
        name="Solar Sell",
        device_class=SensorDeviceClass.ENUM,
        options=["On", "Off", "Unknown"],
        value_fn=_bool_to_str,
    ),
    SolArkConfigSensorDescription(
        key="config_time_of_use",
        api_key="peakAndVallery",
        name="Time of Use",
        device_class=SensorDeviceClass.ENUM,
        options=["On", "Off", "Unknown"],
        value_fn=_bool_to_str,
    ),
    # Mode settings
    SolArkConfigSensorDescription(
        key="config_work_mode",
        api_key="sysWorkMode",
        name="Work Mode",
        device_class=SensorDeviceClass.ENUM,
        options=["grid_selling", "limited_to_load", "limited_to_home", "Unknown"],
        value_fn=_work_mode_to_str,
    ),
    SolArkConfigSensorDescription(
        key="config_energy_mode",
        api_key="energyMode",
        name="Energy Mode",
        device_class=SensorDeviceClass.ENUM,
        options=["battery_first", "load_first", "Unknown"],
        value_fn=_energy_mode_to_str,
    ),
]

# Day toggle sensors
for day_key, day_label in (
    ("mondayOn", "Monday"),
    ("tuesdayOn", "Tuesday"),
    ("wednesdayOn", "Wednesday"),
    ("thursdayOn", "Thursday"),
    ("fridayOn", "Friday"),
    ("saturdayOn", "Saturday"),
    ("sundayOn", "Sunday"),
):
    CONFIG_SENSOR_DESCRIPTIONS.append(
        SolArkConfigSensorDescription(
            key=f"config_{day_label.lower()}",
            api_key=day_key,
            name=f"Time of Use {day_label}",
            device_class=SensorDeviceClass.ENUM,
            options=["On", "Off", "Unknown"],
            value_fn=_bool_to_str,
        )
    )

# Slot sensors (1-6)
for slot in range(1, 7):
    CONFIG_SENSOR_DESCRIPTIONS.extend(
        [
            SolArkConfigSensorDescription(
                key=f"config_slot{slot}_time",
                api_key=f"sellTime{slot}",
                name=f"Slot {slot} Time",
            ),
            SolArkConfigSensorDescription(
                key=f"config_slot{slot}_power",
                api_key=f"sellTime{slot}Pac",
                name=f"Slot {slot} Power",
                native_unit_of_measurement="W",
                device_class=SensorDeviceClass.POWER,
            ),
            SolArkConfigSensorDescription(
                key=f"config_slot{slot}_soc",
                api_key=f"cap{slot}",
                name=f"Slot {slot} Battery SOC",
                native_unit_of_measurement="%",
            ),
        ]
    )


# Slot mode sensors need special handling (computed from two API fields)
SLOT_MODE_SENSORS: list[tuple[int, str]] = [
    (slot, f"config_slot{slot}_mode") for slot in range(1, 7)
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolArk sensors from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data["coordinator"]
    settings_coordinator: DataUpdateCoordinator = data["settings_coordinator"]

    entities: list[SensorEntity] = [
        SolArkSensor(coordinator, entry, desc) for desc in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities, update_before_add=True)

    energy_entities = _build_energy_entities(hass, entry, coordinator)
    if energy_entities:
        async_add_entities(energy_entities, update_before_add=True)

    # Add configuration sensors (read-only, from settings coordinator)
    _LOGGER.debug(
        "Creating %d config sensors with settings_coordinator data: %s",
        len(CONFIG_SENSOR_DESCRIPTIONS),
        settings_coordinator.data,
    )
    config_entities: list[SensorEntity] = []
    for desc in CONFIG_SENSOR_DESCRIPTIONS:
        try:
            config_entities.append(
                SolArkConfigSensor(settings_coordinator, entry, desc)
            )
        except Exception as err:
            _LOGGER.error("Failed to create config sensor %s: %s", desc.key, err)
    # Add slot mode sensors (computed from two API fields)
    for slot, key in SLOT_MODE_SENSORS:
        try:
            config_entities.append(
                SolArkSlotModeConfigSensor(settings_coordinator, entry, slot, key)
            )
        except Exception as err:
            _LOGGER.error("Failed to create slot mode sensor %s: %s", key, err)
    _LOGGER.debug("Adding %d config entities", len(config_entities))
    async_add_entities(config_entities, update_before_add=True)
    _LOGGER.debug("Config entities added successfully")

    hass.async_create_task(_async_fix_grid_power_entity_id(hass, entry))


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
        self._attr_suggested_object_id = f"{DOMAIN}_{description.key}"
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


class SolArkConfigSensor(CoordinatorEntity, SensorEntity):
    """Read-only sensor for inverter configuration values."""

    entity_description: SolArkConfigSensorDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        description: SolArkConfigSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_suggested_object_id = f"{DOMAIN}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }

    @property
    def native_value(self) -> Any:
        settings = (self.coordinator.data or {}).get("settings") or {}
        value = settings.get(self.entity_description.api_key)
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(value)
        return value


class SolArkSlotModeConfigSensor(CoordinatorEntity, SensorEntity):
    """Read-only sensor for slot mode (computed from time{N}on + genTime{N}on)."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        slot: int,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_suggested_object_id = f"{DOMAIN}_{key}"
        self._attr_name = f"Slot {slot} Mode"
        self._attr_has_entity_name = True
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["off", "sell", "charge", "both", "Unknown"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "SolArk",
            "manufacturer": "SolArk",
        }

    @property
    def native_value(self) -> str:
        settings = (self.coordinator.data or {}).get("settings") or {}
        time_on = settings.get(f"time{self._slot}on")
        gen_on = settings.get(f"genTime{self._slot}on")
        if time_on is None or gen_on is None:
            return "Unknown"
        return slot_mode_from_api(_coerce_bool(time_on), _coerce_bool(gen_on))


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
        self._attr_suggested_object_id = f"{DOMAIN}_{description.key}"
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
    sensor._attr_suggested_object_id = f"{DOMAIN}_{description.key}"
    if not getattr(sensor, "unique_id", None):
        sensor._attr_unique_id = unique_id
    if getattr(sensor, "device_class", None) is None:
        sensor._attr_device_class = SensorDeviceClass.ENERGY
    if getattr(sensor, "state_class", None) is None:
        sensor._attr_state_class = SensorStateClass.TOTAL_INCREASING
    return sensor


async def _async_fix_grid_power_entity_id(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Ensure grid power entity_id stays consistent after re-adds."""
    await asyncio.sleep(0)
    registry = er.async_get(hass)
    unique_id = f"{entry.entry_id}_grid_power"
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    if not entity_id:
        return
    desired = f"sensor.{DOMAIN}_grid_power"
    if entity_id == desired:
        return
    if registry.async_get(desired):
        _LOGGER.debug(
            "Grid power entity id already in use (%s); keeping %s",
            desired,
            entity_id,
        )
        return
    registry.async_update_entity(entity_id, new_entity_id=desired)


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
