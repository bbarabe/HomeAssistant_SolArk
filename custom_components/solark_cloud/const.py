"""Constants for the Sol-Ark Cloud integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "solark_cloud"

# Configuration keys
CONF_PLANT_ID: Final = "plant_id"
CONF_BASE_URL: Final = "base_url"
CONF_AUTH_MODE: Final = "auth_mode"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Default values
DEFAULT_BASE_URL: Final = "https://api.solarkcloud.com"
DEFAULT_AUTH_MODE: Final = "auto"
DEFAULT_SCAN_INTERVAL: Final = 120  # seconds

# Base URL options
BASE_URL_OPTIONS: Final = [
    "https://api.solarkcloud.com",
    "https://www.mysolark.com"
]

# Auth mode options
AUTH_MODE_OPTIONS: Final = [
    "auto",
    "strict",
    "legacy"
]

# Sensor types
SENSOR_TYPES: Final = {
    "pv_power": {
        "name": "PV Power",
        "unit": "W",
        "icon": "mdi:solar-power",
        "device_class": "power",
        "state_class": "measurement"
    },
    "load_power": {
        "name": "Load Power",
        "unit": "W",
        "icon": "mdi:home-lightning-bolt",
        "device_class": "power",
        "state_class": "measurement"
    },
    "grid_import_power": {
        "name": "Grid Import Power",
        "unit": "W",
        "icon": "mdi:transmission-tower-export",
        "device_class": "power",
        "state_class": "measurement"
    },
    "grid_export_power": {
        "name": "Grid Export Power",
        "unit": "W",
        "icon": "mdi:transmission-tower-import",
        "device_class": "power",
        "state_class": "measurement"
    },
    "battery_power": {
        "name": "Battery Power",
        "unit": "W",
        "icon": "mdi:battery-charging",
        "device_class": "power",
        "state_class": "measurement"
    },
    "battery_soc": {
        "name": "Battery State of Charge",
        "unit": "%",
        "icon": "mdi:battery",
        "device_class": "battery",
        "state_class": "measurement"
    },
    "energy_today": {
        "name": "Energy Today",
        "unit": "kWh",
        "icon": "mdi:solar-power",
        "device_class": "energy",
        "state_class": "total_increasing"
    },
    "last_error": {
        "name": "Last Error",
        "unit": None,
        "icon": "mdi:alert-circle",
        "device_class": None,
        "state_class": None
    }
}

# API endpoints
ENDPOINT_LOGIN: Final = "/rest/account/login"
ENDPOINT_PLANT_DATA: Final = "/rest/plant/getPlantData"

# Update intervals
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 3600
