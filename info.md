# Sol-Ark Cloud Integration

{% if installed %}
## Installed Version: {{ installed }}
{% endif %}

{% if version_installed %}
## Available Version: {{ version_installed }}
{% endif %}

{% if pending_update %}
## ⚠️ Update Available
{% endif %}

## About

A custom Home Assistant integration that connects to Sol-Ark Cloud (MySolArk portal) to retrieve live solar inverter and battery data.

## Features

- 🔐 **Secure Authentication** with MySolArk credentials
- 🔄 **Flexible Auth Modes**: Auto, Strict, and Legacy authentication support
- 📊 **Comprehensive Sensors**: PV Power, Load Power, Grid Import/Export, Battery Power & SoC, Energy Today
- ⚙️ **Full UI Configuration** - No YAML editing required
- 🔧 **Options Flow** - Easily update settings without recreating the integration
- 📡 **Configurable Update Interval** - Balance between data freshness and API load
- 🌐 **Multiple Base URL Support** - Works with api.solarkcloud.com and www.mysolark.com

## Configuration

After installation:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Sol-Ark Cloud"
4. Enter your MySolArk credentials and Plant ID
5. Configure optional settings (Base URL, Auth Mode, Update Interval)
6. Submit and enjoy your solar monitoring!

## Finding Your Plant ID

1. Log into [MySolArk](https://www.mysolark.com)
2. Navigate to your plant dashboard
3. Look at the URL - it will contain your plant ID
4. Example: `https://www.mysolark.com/plant/detail/12345` → Plant ID is `12345`

## Sensors

After configuration, you'll have 8 sensors:

- **PV Power (W)** - Solar panel power production
- **Load Power (W)** - Current home consumption
- **Grid Import Power (W)** - Power imported from grid
- **Grid Export Power (W)** - Power exported to grid
- **Battery Power (W)** - Battery charge/discharge (positive = discharge, negative = charge)
- **Battery State of Charge (%)** - Battery level
- **Energy Today (kWh)** - Total energy produced today
- **Last Error** - System diagnostics

## Support

- [Documentation](https://github.com/HammondAutomationHub/HomeAssistant_SolArk)
- [Report Issues](https://github.com/HammondAutomationHub/HomeAssistant_SolArk/issues)
- [Quick Start Guide](https://github.com/HammondAutomationHub/HomeAssistant_SolArk/blob/main/QUICKSTART.md)

## Requirements

- Home Assistant 2023.1.0 or newer
- Active MySolArk account
- Your Sol-Ark Plant ID

---

Made with ❤️ for the Home Assistant community
