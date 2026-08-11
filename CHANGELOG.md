# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### 🔒 Security

- Username, password and OAuth tokens are redacted from debug/error logs. The
  login handlers previously logged full response bodies, which contain
  `access_token` and `refresh_token`. (upstream `d336443`)
- Diagnostics downloads now redact token fields as well as credentials.
  (upstream `d336443`)

### ✨ Improvements

- **Auto-discover API URL** — the integration reads `VUE_APP_BASE_API` from the
  Sol-Ark portal frontend at startup, so a future API host migration is picked
  up automatically instead of needing a code change. Toggleable during setup and
  in **Configure**; the manual **API URL** remains as override and as fallback
  when discovery fails. (upstream `11072e0`, `6ed5b09`)
- Retired Sol-Ark hosts are rewritten to current defaults on upgrade. This now
  covers `base_url` (`mysolark.com` → `www.solarkcloud.com`) as well as
  `api_url`, and additionally handles `ecsprod-api.solarkcloud.com`.
  (upstream `11072e0`, `6ed5b09`)

### 🐛 Fixes

- The legacy login fallback used a hardcoded `api.solarkcloud.com` instead of
  the configured `api_url`, so it would have kept talking to a retired host
  after the p2 migration. (upstream `d336443`)
- PV power now includes `minPower` (microinverter / AC-coupled PV) from the
  energy flow endpoint. (upstream `62d0b49`)
- Placeholder MPPT volt/current ramps returned by some `dy/store` payloads are
  no longer summed into PV power as if they were live string data. The MPPT sum
  is now a true last resort, used only when the flow endpoint reports no PV.
  (upstream `62d0b49`)
- Battery SOC only falls back to `curCap`/`batteryCap` when `curCap` is actually
  populated; a missing `curCap` previously reported a confident 0%.
  (upstream `62d0b49`)
- The plant `/realtime` endpoint is used as an energy fallback when the inverter
  list yields nothing. Unlike upstream, it does **not** override the
  per-inverter sum: on a probed plant the two agreed on `etoday` (56.7 kWh) but
  differed by ~22 MWh on `etotal`, because the plant figure counts hardware no
  longer in the inverter list. Preferring it would inject a one-time step into
  a `TOTAL_INCREASING` sensor and corrupt energy dashboard statistics.
  (diverges from upstream `62d0b49`)
- `energy_today` and `energy_total` now sum production across all inverters in
  the plant instead of reporting only the first inverter in the API response.
  On multi-inverter plants these sensors were previously under-reporting (e.g.
  showing one inverter's ~7.5 kWh instead of the plant total). Flow-derived
  values (PV, load, grid, battery, SOC) were already plant-wide and are
  unchanged.

## [5.2.0] - 2026-01-30

### ✨ Improvements

- Added System Work Mode configuration entities (numbers, switches, time).
- Added write-access toggle in the config flow (disabled by default).
- Settings are fetched/written only against the master inverter.
- Master inverter SN is cached in memory to reduce repeated lookups.
- Options updates now reload the integration so write access toggles take effect.
- Settings entities now optimistically show new values briefly and retry refresh
  to handle API propagation delays.
- Work Mode and Energy Pattern are now select entities with labeled options.
- Added Time Of Use day-of-week switches.
- Added Home Consumption Energy sensor (integrated from load power).
- Added config entry migration to seed new options (allow write access).
- Grid power entity ID is now normalized to `sensor.solark_grid_power` after
  re-adding the integration.
- Settings polling now briefly accelerates after a write (about every 15
  seconds for up to a minute) while pending changes exist.

### 📚 Documentation

- Added configuration write-access guidance.

## [5.1.1] - 2026-01-30

### ✨ Improvements

- Added native battery charge/discharge power sensors:
  - `sensor.solark_battery_charge_power`
  - `sensor.solark_battery_discharge_power`
- Added native battery charge/discharge energy sensors using the integration
  method (trapezoidal):
  - `sensor.solark_battery_charge_energy`
  - `sensor.solark_battery_discharge_energy`

### 📚 Documentation

- Updated Energy dashboard setup to use built-in battery energy sensors.
- Updated sensor lists and counts in README and Quick Start.
- Fixed options flow initialization for older Home Assistant versions.

## [5.1.0] - 2026-01-29

### ✨ Improvements

- Added native energy sensors for grid import/export:
  - `sensor.solark_grid_import_energy`
  - `sensor.solark_grid_export_energy`
- Added status sensors:
  - `sensor.solark_grid_status`
  - `sensor.solark_generator_status`
- Grid import/export now derives from `gridOrMeterPower` + direction flags when
  no CT meter is present.
- Battery power sign is inferred from flow direction flags (`toBat`/`batTo`).
- Logging now respects Home Assistant's logging configuration (no forced file
  logging).

### 📚 Documentation

- Updated Energy dashboard setup to use built-in energy sensors.
- Updated sensor lists and troubleshooting guidance.

## [5.0.0] - 2024-11-21

### 🎉 Major Features

- **Energy Dashboard Compatible** - Full support for Home Assistant's Energy dashboard
  - Track solar production with `sensor.solark_energy_total`
  - Monitor grid consumption and export
  - Battery energy tracking support
  - Long-term statistics automatically recorded
  - Cost tracking and energy flow diagrams

### ⚠️ Breaking Changes

- **Entity ID Format Changed**
  - Old: `sensor.solark_plant_pv_power`
  - New: `sensor.solark_pv_power`
  - **Migration Required:** Existing users must remove and re-add the integration
  - **Action Required:** Update all automations, dashboards, and scripts with new entity IDs

### ✨ Improvements

- Added `state_class` attribute to all sensors for statistics tracking
  - Power sensors: `state_class: measurement`
  - Energy sensors: `state_class: total_increasing`
- Battery SOC now uses proper `BATTERY` device class
- Device name simplified from "SolArk Plant" to "SolArk"
- Cleaner, more predictable entity IDs
- Enhanced sensor attributes for better Energy dashboard integration

### 📚 Documentation

- **New:** Complete Energy Dashboard setup guide (ENERGY_DASHBOARD_SETUP.md)
- **New:** Quick Start guide for new users (QUICKSTART.md)
- **Updated:** README with comprehensive troubleshooting and examples
- **Added:** Dashboard YAML configuration examples
- **Added:** Automation and template sensor examples
- **Added:** Energy Dashboard compatibility badge

### 🔧 Technical Changes

- Added `_attr_has_entity_name = True` to sensor entities
- Updated sensor descriptions with proper `state_class` attributes
- Improved entity naming for Home Assistant entity system
- All sensors now properly support long-term statistics

### 🔄 Migration Guide for Existing Users

1. **Backup Configuration**
   - Note your Plant ID and credentials
   - Export any dashboards or automations using SolArk sensors

2. **Remove Old Integration**
   - Go to Settings → Devices & Services
   - Find "SolArk Cloud"
   - Click three dots (⋮) → Delete

3. **Update Integration**
   - Update via HACS or manually install new version
   - Restart Home Assistant

4. **Re-add Integration**
   - Settings → Devices & Services → + ADD INTEGRATION
   - Search "SolArk Cloud"
   - Enter your credentials
   - Sensors created with new entity IDs

5. **Update References**
   - Update automations with new entity IDs
   - Update dashboards
   - Update template sensors

### 📋 Entity ID Mapping

| Old Entity ID | New Entity ID |
|---------------|---------------|
| `sensor.solark_plant_pv_power` | `sensor.solark_pv_power` |
| `sensor.solark_plant_battery_power` | `sensor.solark_battery_power` |
| `sensor.solark_plant_battery_soc` | `sensor.solark_battery_soc` |
| `sensor.solark_plant_grid_power` | `sensor.solark_grid_power` |
| `sensor.solark_plant_load_power` | `sensor.solark_load_power` |
| `sensor.solark_plant_grid_import_power` | `sensor.solark_grid_import_power` |
| `sensor.solark_plant_grid_export_power` | `sensor.solark_grid_export_power` |
| `sensor.solark_plant_energy_today` | `sensor.solark_energy_today` |
| `sensor.solark_plant_energy_total` | `sensor.solark_energy_total` |

---

## [4.x] - Previous Versions

See git history for previous version changes.
