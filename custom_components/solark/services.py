"""SolArk service definitions and parameter mapping."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.helpers import config_validation as cv

# Work mode mapping: service value -> API value
WORK_MODE_MAP = {
    "grid_selling": 0,
    "limited_to_load": 1,
    "limited_to_home": 2,
}
WORK_MODE_REVERSE = {v: k for k, v in WORK_MODE_MAP.items()}

# Energy mode mapping: service value -> API value
ENERGY_MODE_MAP = {
    "battery_first": 0,
    "load_first": 1,
}
ENERGY_MODE_REVERSE = {v: k for k, v in ENERGY_MODE_MAP.items()}

# Slot mode mapping: service value -> (time{N}on, genTime{N}on)
# time{N}on = charge enabled, genTime{N}on = sell enabled
SLOT_MODE_MAP = {
    "off": (False, False),
    "sell": (False, True),
    "charge": (True, False),
    "both": (True, True),
}


def slot_mode_from_api(time_on: bool, gen_on: bool) -> str:
    """Convert API values to slot mode string."""
    for mode, (t, g) in SLOT_MODE_MAP.items():
        if t == time_on and g == gen_on:
            return mode
    return "off"


# Simple parameter to API key mapping (direct 1:1)
SIMPLE_PARAM_MAP = {
    # Power limits
    "max_solar_power": "solarMaxSellPower",
    "zero_export_power": "zeroExportPower",
    "max_sell_power": "pvMaxLimit",
    # Boolean toggles
    "solar_sell": "solarSell",
    "time_of_use": "peakAndVallery",
    # Day toggles
    "monday": "mondayOn",
    "tuesday": "tuesdayOn",
    "wednesday": "wednesdayOn",
    "thursday": "thursdayOn",
    "friday": "fridayOn",
    "saturday": "saturdayOn",
    "sunday": "sundayOn",
}

# Slot parameters (per slot 1-6)
SLOT_PARAMS = {
    "time": "sellTime",  # sellTime1, sellTime2, etc.
    "power": "sellTime{}Pac",  # sellTime1Pac, etc.
    "soc": "cap",  # cap1, cap2, etc.
}


def build_api_updates(service_data: dict[str, Any]) -> dict[str, Any]:
    """Convert service call parameters to API update dict."""
    updates: dict[str, Any] = {}

    # Simple 1:1 mappings
    for param, api_key in SIMPLE_PARAM_MAP.items():
        if param in service_data:
            value = service_data[param]
            # Convert booleans to int for API (solarSell, peakAndVallery)
            if api_key in ("solarSell", "peakAndVallery"):
                value = 1 if value else 0
            updates[api_key] = value

    # Work mode
    if "work_mode" in service_data:
        mode = service_data["work_mode"]
        if mode in WORK_MODE_MAP:
            updates["sysWorkMode"] = WORK_MODE_MAP[mode]

    # Energy mode
    if "energy_mode" in service_data:
        mode = service_data["energy_mode"]
        if mode in ENERGY_MODE_MAP:
            updates["energyMode"] = ENERGY_MODE_MAP[mode]

    # Slot parameters (1-6)
    for slot in range(1, 7):
        # Slot time
        time_key = f"slot{slot}_time"
        if time_key in service_data:
            updates[f"sellTime{slot}"] = service_data[time_key]

        # Slot power
        power_key = f"slot{slot}_power"
        if power_key in service_data:
            updates[f"sellTime{slot}Pac"] = int(service_data[power_key])

        # Slot SOC
        soc_key = f"slot{slot}_soc"
        if soc_key in service_data:
            updates[f"cap{slot}"] = int(service_data[soc_key])

        # Slot mode (complex: maps to two API fields)
        mode_key = f"slot{slot}_mode"
        if mode_key in service_data:
            mode = service_data[mode_key]
            if mode in SLOT_MODE_MAP:
                time_on, gen_on = SLOT_MODE_MAP[mode]
                updates[f"time{slot}on"] = time_on
                updates[f"genTime{slot}on"] = gen_on

    return updates


# Voluptuous schema for service validation
CONFIGURE_INVERTER_SCHEMA = vol.Schema(
    {
        # Power limits
        vol.Optional("max_solar_power"): vol.All(
            vol.Coerce(int), vol.Range(min=500, max=19500)
        ),
        vol.Optional("zero_export_power"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=500)
        ),
        vol.Optional("max_sell_power"): vol.All(
            vol.Coerce(int), vol.Range(min=500, max=32000)
        ),
        # Boolean toggles
        vol.Optional("solar_sell"): cv.boolean,
        vol.Optional("time_of_use"): cv.boolean,
        # Work mode
        vol.Optional("work_mode"): vol.In(list(WORK_MODE_MAP.keys())),
        # Energy mode
        vol.Optional("energy_mode"): vol.In(list(ENERGY_MODE_MAP.keys())),
        # Day toggles
        vol.Optional("monday"): cv.boolean,
        vol.Optional("tuesday"): cv.boolean,
        vol.Optional("wednesday"): cv.boolean,
        vol.Optional("thursday"): cv.boolean,
        vol.Optional("friday"): cv.boolean,
        vol.Optional("saturday"): cv.boolean,
        vol.Optional("sunday"): cv.boolean,
        # Slot 1
        vol.Optional("slot1_time"): cv.time,
        vol.Optional("slot1_power"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=14000)
        ),
        vol.Optional("slot1_soc"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("slot1_mode"): vol.In(list(SLOT_MODE_MAP.keys())),
        # Slot 2
        vol.Optional("slot2_time"): cv.time,
        vol.Optional("slot2_power"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=14000)
        ),
        vol.Optional("slot2_soc"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("slot2_mode"): vol.In(list(SLOT_MODE_MAP.keys())),
        # Slot 3
        vol.Optional("slot3_time"): cv.time,
        vol.Optional("slot3_power"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=14000)
        ),
        vol.Optional("slot3_soc"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("slot3_mode"): vol.In(list(SLOT_MODE_MAP.keys())),
        # Slot 4
        vol.Optional("slot4_time"): cv.time,
        vol.Optional("slot4_power"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=14000)
        ),
        vol.Optional("slot4_soc"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("slot4_mode"): vol.In(list(SLOT_MODE_MAP.keys())),
        # Slot 5
        vol.Optional("slot5_time"): cv.time,
        vol.Optional("slot5_power"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=14000)
        ),
        vol.Optional("slot5_soc"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("slot5_mode"): vol.In(list(SLOT_MODE_MAP.keys())),
        # Slot 6
        vol.Optional("slot6_time"): cv.time,
        vol.Optional("slot6_power"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=14000)
        ),
        vol.Optional("slot6_soc"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("slot6_mode"): vol.In(list(SLOT_MODE_MAP.keys())),
    }
)
