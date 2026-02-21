# SolArk Cloud Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/HammondAutomationHub/HomeAssistant_SolArk.svg)](https://github.com/HammondAutomationHub/HomeAssistant_SolArk/releases)
[![Energy Dashboard](https://img.shields.io/badge/Energy%20Dashboard-Compatible-green.svg)](https://www.home-assistant.io/home-energy-management/)

A Home Assistant custom integration for Sol-Ark inverter systems that connects to the SolArk Cloud API. Monitor your solar system with real-time data and track long-term energy production with full Energy Dashboard support.

## 🌟 Key Features

- **Energy Dashboard Compatible** - Native support for Home Assistant's Energy dashboard
- **Real-time Monitoring** - Live power flow tracking (PV, Battery, Grid, Load)
- **Cloud-based** - No physical connections required
- **18 Comprehensive Sensors** - All critical solar system metrics
- **Beautiful Dashboards** - Pre-built power flow visualizations
- **Long-term Statistics** - Automatic energy tracking and historical data
- **Easy Setup** - Simple configuration through Home Assistant UI

## 📊 Sensors Provided

| Entity ID | Description | Unit | Energy Dashboard |
|-----------|-------------|------|------------------|
| `sensor.solark_pv_power` | Solar panel power | W | Power only |
| `sensor.solark_battery_power` | Battery charge/discharge | W | Power only |
| `sensor.solark_battery_charge_power` | Battery charge power | W | Power only |
| `sensor.solark_battery_discharge_power` | Battery discharge power | W | Power only |
| `sensor.solark_battery_soc` | Battery state of charge | % | Battery level |
| `sensor.solark_grid_power` | Net grid power | W | Power only |
| `sensor.solark_load_power` | Home consumption | W | Power only |
| `sensor.solark_grid_import_power` | Grid import | W | Power only |
| `sensor.solark_grid_export_power` | Grid export | W | Power only |
| `sensor.solark_grid_import_energy` | Grid import energy | kWh | ✅ Direct use |
| `sensor.solark_grid_export_energy` | Grid export energy | kWh | ✅ Direct use |
| `sensor.solark_battery_charge_energy` | Battery charge energy | kWh | ✅ Direct use |
| `sensor.solark_battery_discharge_energy` | Battery discharge energy | kWh | ✅ Direct use |
| `sensor.solark_home_consumption_energy` | Home consumption energy | kWh | ✅ Direct use |
| `sensor.solark_grid_status` | Grid status | - | Status |
| `sensor.solark_generator_status` | Generator status | - | Status |
| `sensor.solark_ac_relay_status` | AC relay status (grid connection) | - | Status |
| `sensor.solark_energy_today` | Daily production | kWh | ✅ Direct use |
| `sensor.solark_energy_total` | Lifetime production | kWh | ✅ Solar production |

**Note:** Battery power: positive = discharging, negative = charging

## 📋 Requirements

- Home Assistant 2023.5.0 or newer
- Sol-Ark inverter (12K, 15K, 8K, 5K models)
- Active Sol-Ark Cloud account
- Your Plant ID from Sol-Ark portal

## 🚀 Installation

### Via HACS (Recommended)

1. Open **HACS** → **Integrations**
2. Click **⋮** → **Custom repositories**
3. Add: `https://github.com/HammondAutomationHub/HomeAssistant_SolArk`
4. Category: **Integration**
5. Find "SolArk Cloud" and click **Download**
6. Restart Home Assistant

### Manual Installation

1. Download latest release
2. Copy `custom_components/solark` to your `/config/custom_components/` directory
3. Restart Home Assistant

## ⚙️ Configuration

### 1. Get Your Plant ID

1. Log into [mysolark.com](https://www.mysolark.com)
2. Navigate to your system
3. Check the URL: `https://www.mysolark.com/plant/12345`
4. Your Plant ID is `12345`

### 2. Add Integration

1. **Settings** → **Devices & Services** → **+ ADD INTEGRATION**
2. Search "SolArk Cloud"
3. Enter:
   - **Username**: Your Sol-Ark email
   - **Password**: Your Sol-Ark password
   - **Plant ID**: From step 1
   - **Scan Interval**: 30 (seconds)
4. Click **SUBMIT**

### 3. Verify

- Go to **Developer Tools** → **States**
- Search `solark`
- Verify 18 sensors with live data

## ⚙️ System Work Mode Settings (Configuration Entities)

The integration exposes System Work Mode settings as configuration entities
(Number, Switch, Time) under the **Configuration** group for the SolArk device.

**Safety default:** write access is disabled by default.

To enable writes:
1. Open **Settings** → **Devices & Services** → **SolArk Cloud**
2. Click **Configure**
3. Toggle **Allow write access**

When write access is off, changes are blocked and will raise an error.

Note: SolArk's API maps Charge Time to `timeXon` fields and Sell Time to
`genTimeXon`. Each time slot uses a single Sell/Charge select that updates
both fields together. When you change multiple settings quickly, the
integration temporarily remembers recent writes (about 30 seconds) and
clears them after a successful fetch (or once the server reflects them) so
API lag does not overwrite your last change.
After a write, the settings coordinator also polls more frequently (about
every 15 seconds for up to a minute) while pending changes exist.

## 🧪 CLI Testing (Optional)

If you want to test the SolArk Cloud API from your machine:

1. Copy `solark_secrets.template.json` to `solark_secrets.json`
2. Fill in your Sol-Ark username/password and Plant ID
3. Run:
```bash
python -m solark_cli --secrets solark_secrets.json --combined --parsed
```

## ⚡ Energy Dashboard Setup

Your integration is fully compatible with Home Assistant's Energy dashboard!
Grid import/export and battery charge/discharge energy sensors are provided
directly by the integration, so no helper setup is required.

### Quick Setup

1. **Settings** → **Dashboards** → **Energy**
2. **Solar Production** → Add Production
   - Select: `sensor.solark_energy_total`
3. **Grid Consumption**:
   - Select `sensor.solark_grid_import_energy`
4. **Grid Return** (if you export):
   - Select `sensor.solark_grid_export_energy`

**📚 Full Guide:** See [ENERGY_DASHBOARD_SETUP.md](ENERGY_DASHBOARD_SETUP.md) for complete instructions including battery tracking.

## 📱 Dashboard Examples

### Power Flow Dashboard

Beautiful real-time monitoring with dynamic power flow indicators:

**Features:**
- Live power values with color coding
- Battery status with dynamic icons
- 24-hour historical charts
- Energy production statistics

**Requirements:**
- [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom) (HACS)
- [ApexCharts Card](https://github.com/RomRider/apexcharts-card) (HACS)

**Installation:**

**Option A - UI Method:**
1. Copy `dashboards/solark_flow.yaml` content
2. **Settings** → **Dashboards** → **+ ADD DASHBOARD**
3. **⋮** → **Edit Dashboard** → **⋮** → **Raw configuration editor**
4. Paste and save

**Option B - YAML File:**
1. Copy `solark_flow.yaml` to `/config/dashboards/`
2. Add to `configuration.yaml`:
```yaml
lovelace:
  mode: storage
  dashboards:
    solark-power:
      mode: yaml
      title: SolArk Power Flow
      icon: mdi:solar-power
      show_in_sidebar: true
      filename: dashboards/solark_flow.yaml
```
3. Restart Home Assistant

## 🤖 Automation Examples

### Low Battery Alert
```yaml
automation:
  - alias: "Low Battery Warning"
    trigger:
      platform: numeric_state
      entity_id: sensor.solark_battery_soc
      below: 20
    action:
      service: notify.mobile_app
      data:
        title: "Low Battery"
        message: "Battery at {{ states('sensor.solark_battery_soc') }}%"
```

### Excess Solar Notification
```yaml
automation:
  - alias: "Exporting to Grid"
    trigger:
      platform: numeric_state
      entity_id: sensor.solark_grid_export_power
      above: 2000
      for: "00:05:00"
    action:
      service: notify.mobile_app
      data:
        message: "Exporting {{ states('sensor.solark_grid_export_power') }}W"
```

### Battery Full Alert
```yaml
automation:
  - alias: "Battery Fully Charged"
    trigger:
      platform: numeric_state
      entity_id: sensor.solark_battery_soc
      above: 95
    condition:
      condition: numeric_state
      entity_id: sensor.solark_battery_power
      below: 100
    action:
      service: notify.mobile_app
      data:
        message: "Battery full at {{ states('sensor.solark_battery_soc') }}%"
```

## 📐 Template Sensors

### Self-Consumption Percentage
```yaml
template:
  - sensor:
      - name: "Solar Self-Consumption"
        unit_of_measurement: "%"
        state: >
          {% set pv = states('sensor.solark_pv_power') | float(0) %}
          {% set export = states('sensor.solark_grid_export_power') | float(0) %}
          {% if pv > 0 %}
            {{ ((pv - export) / pv * 100) | round(1) }}
          {% else %}
            0
          {% endif %}
```

### Battery Status Text
```yaml
template:
  - sensor:
      - name: "Battery Status"
        state: >
          {% set power = states('sensor.solark_battery_power') | float(0) %}
          {% if power > 100 %}
            Discharging
          {% elif power < -100 %}
            Charging
          {% else %}
            Idle
          {% endif %}
```

## 🔧 Troubleshooting

### Integration Won't Connect
- Verify credentials at mysolark.com
- Confirm Plant ID is correct
- Check logs: **Settings** → **System** → **Logs**

### Sensors Show "Unavailable"
- Check SolArk Cloud service status
- Increase scan interval to 60 seconds
- Reload integration
- Check Home Assistant logs for `custom_components.solark`

### Grid Power Entity ID Looks Wrong
- The net grid power entity should be `sensor.solark_grid_power`.
- If you see `sensor.solark_grid_power_net` after reinstalling, reload the
  integration or restart Home Assistant so the entity registry rename runs.

### Dashboard Shows Blank
1. Verify sensors exist: **Developer Tools** → **States**
2. Install Mushroom Cards and ApexCharts Card
3. Restart Home Assistant
4. Clear browser cache (Ctrl+Shift+R)

### Energy Dashboard Issues
- Wait 1-2 hours for statistics to build
- Verify `sensor.solark_energy_total` has data
- Check sensor has `state_class: total_increasing`
- See [ENERGY_DASHBOARD_SETUP.md](ENERGY_DASHBOARD_SETUP.md)

### Enable Debug Logging
```yaml
# configuration.yaml
logger:
  logs:
    custom_components.solark: debug
```

Then check **Settings** → **System** → **Logs**

## 🏗️ Technical Details

### Architecture
- Uses `DataUpdateCoordinator` for efficient polling
- OAuth 2.0 authentication with auto-refresh
- Combines data from two API endpoints:
  - Energy flow: `/api/v1/plant/energy/{plant_id}/flow`
  - Live data: `/api/v1/dy/store/{sn}/read`

### Statistics Support
- Power sensors: `state_class: measurement`
- Energy sensors: `state_class: total_increasing`
- Long-term statistics automatically recorded
- Compatible with Energy dashboard

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit Pull Request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/HammondAutomationHub/HomeAssistant_SolArk/issues)
- **Discussions**: [GitHub Discussions](https://github.com/HammondAutomationHub/HomeAssistant_SolArk/discussions)
- **Community**: [Home Assistant Forums](https://community.home-assistant.io/)

## 📄 License

Provided as-is with no warranty. Use at your own risk.

## 🙏 Acknowledgments

- Home Assistant community
- Sol-Ark for API access
- All contributors

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Note:** Not officially affiliated with Sol-Ark. Community-developed integration.

**Version:** 5.2.0 | **Supports:** Sol-Ark 5K/8K/12K/15K | **HA:** 2023.5.0+
