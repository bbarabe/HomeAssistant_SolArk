# Changelog

All notable changes to this project will be documented in this file.

## [5.3.0] - 2026-08-11

Everything below is relative to 5.0.2 and includes all of its changes. Existing
installs migrate automatically — no need to remove and re-add the integration,
and no entity IDs change.

### ✨ New Features

- **Inverter configuration visibility** — the System Work Mode programming is
  now exposed as read-only diagnostic sensors: Work Mode, Energy Pattern,
  Solar Sell, Time-Of-Use enable, the six TOU slots (time, power, battery SOC,
  charge flags), day-of-week TOU flags, Max Solar Power, Max Sell Power, and
  Zero Export Power.
- **`solark.configure_inverter` action** — writes System Work Mode settings
  (work mode, energy pattern, TOU slots, sell/charge toggles, power limits) to
  the master inverter. Gated behind a new **Allow write access** config option
  (default **off**); with it off the integration is strictly read-only.
  Settings polling briefly accelerates after a write while the cloud
  propagates the change.
- **CLI tool** — `python -m solark_cli` exercises the same API client from the
  command line: plant data, raw endpoint dumps, settings read, gateway list,
  and TOU slot updates. See `CLI.md`. Credentials come from a
  `solark_secrets.json` file (template provided, gitignored).
- **New sensors**:
  - AC Relay Status — reliable on/off-grid detection straight from the
    inverter's relay register.
  - Grid Status and Generator Status.
  - Battery Charge Power / Battery Discharge Power.
  - Battery Charge Energy / Battery Discharge Energy, Grid Import Energy /
    Grid Export Energy, and Home Consumption Energy — native trapezoidal
    integration of the corresponding power sensors, ready for the Energy
    dashboard.

### 🐛 Fixes

- **Multi-inverter plants**: `energy_today` and `energy_total` now sum
  production across every inverter in the plant instead of reporting only the
  first one the API returns.
- The plant `/realtime` endpoint is used as an energy **fallback** when the
  inverter list yields nothing, not as the preferred source (diverges from
  5.0.2). Its `etoday` agrees with the per-inverter sum, but its `etotal`
  carries a large fixed offset on at least some migrated systems — confirmed
  against the plant's own year-by-year history and independent module-level
  monitoring. Preferring it would inject a one-time step into a
  `TOTAL_INCREASING` sensor and corrupt Energy dashboard statistics.
- Spurious zero readings for `energy_today`/`energy_total` during API glitches
  are filtered out instead of being recorded as real drops.
- Energy values refresh on every poll cycle (previously they could go stale
  between date rollovers).
- Date-based API queries (work data, flow data) use the Home Assistant
  configured timezone instead of UTC, fixing wrong-day results in evening
  hours for western timezones.

### 🛡️ Resilience

- Brief cloud API gaps retain last-known status sensor values instead of
  flapping to unknown; a total outage marks entities unavailable rather than
  recording zeros into long-term statistics.
- Prolonged fetch failures raise a Repair issue in Home Assistant so the
  problem is visible without digging through logs.
- Transient cloud failures during Home Assistant startup retry automatically
  instead of leaving the integration failed until manual reload.
- Settings sensors degrade gracefully on accounts that can read telemetry but
  not inverter settings.

### 🔧 Technical

- The API client is extracted into an HA-independent module
  (`solark_client.py`, with `solark_auth.py` for OAuth/legacy login and
  `solark_logging.py` for secret redaction). `api.py` remains as a
  compatibility shim re-exporting the same public names.
- Config entry migration runs automatically (v1 → v4): seeds the write-access
  option, cleans up registry entries from removed platforms, and rewrites
  retired SolArk hosts to the current defaults.
- Master inverter (equipMode 1) is resolved once and cached; settings
  reads/writes always target it.

### 📚 Documentation

- New `CLI.md` (CLI usage) and expanded README sensor/action tables.
- Energy dashboard guide updated for the built-in energy sensors.
- Quick start updated for the current portal (`www.solarkcloud.com`) and
  auto-discovery.

## [5.0.2] - 2026-08-03

### Security

- Username, password, and OAuth tokens are redacted from debug/error logs.
- Removed the always-on `solark_debug.log` file handler (use HA logger instead).

### Fixed

- **PV power** now includes `minPower` (microinverter / AC-coupled PV) from the energy flow endpoint.
- **Battery power** is signed using flow direction flags (`batTo` = discharge +, `toBat` = charge −).
- **Grid import/export** fall back to `gridOrMeterPower` + `gridTo`/`toGrid` when external meter phases are unused.
- **Energy total/today** prefer plant `/realtime` values over inverter-list totals.
- Guard against placeholder `dy/store` MPPT volt/current ramps being treated as live PV.

## [5.0.1] - 2026-08-02

### Fixed

- **SolArk Cloud API host migration** - The portal moved to `www.solarkcloud.com` with API base `https://p2.api.solarkcloud.com`. Defaults and existing installs that still used `mysolark.com` / `ecsprod-api-new.solarkcloud.com` are updated automatically on reload.
- Energy today/total now also falls back to the plant `/realtime` endpoint when inverter summary values are missing.

### Added

- **Auto-discover API URL** - Reads `VUE_APP_BASE_API` from the SolArk portal frontend and stores the resolved API URL on the config entry. Toggleable in setup and Configure options; manual API URL remains as override/fallback.

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
