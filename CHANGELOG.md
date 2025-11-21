# Changelog

## 4.0.4
- Tuned `parse_plant_data` for SolArk 12K STROG/protocol-2:
  - `pv_power` from `pvPower` or MPPT strings (voltN * currentN)
  - `battery_power` from `battPower` or `curVolt * chargeCurrent`
  - `battery_soc` from `battSoc` or `curCap / batteryCap * 100`
  - `grid_import_power` / `grid_export_power` derived from meterA/B/C signed net
  - Ensures all minimal sensors always have numeric values (0.0 fallback).

## 4.0.3
- Trimmed entity set down to a minimal, high-value group:
  - `pv_power`, `battery_power`
  - `grid_import_power`, `grid_export_power`
  - `battery_soc`
  - `energy_today`, `energy_total`
- All other internal / per-string / grid-meter sensors are no longer exposed as entities.

## 4.0.2
- Added additional sensors for debugging and extended telemetry.

## 4.0.1
- Minor packaging for GitHub/HACS and logging verification.

## 4.0.0
- Initial STROG / protocol-2 support with computed PV/load/grid/battery power and SOC.
