# SolArk Cloud – Home Assistant Integration (v4.0.4, minimal sensor set)

Custom Home Assistant integration for SolArk Cloud using the OAuth2 API at
https://ecsprod-api-new.solarkcloud.com behind https://www.mysolark.com.

Tuned for **SolArk 12K** (protocol-2 / STROG) plants.

## Highlights

- OAuth login with legacy fallback for older endpoints.
- Polling interval configurable in config flow and options.
- Advanced file logging to `custom_components/solark/solark_debug.log`.
- Diagnostics support from the Home Assistant UI.
- Minimal, high-value sensors only:
  - PV Power
  - Battery Power
  - Grid Import Power
  - Grid Export Power
  - Battery State of Charge (SOC)
  - Energy Today
  - Energy Total

## Grid import/export semantics

For SolArk 12K, this integration:
- Sums `meterA + meterB + meterC` as a **signed net grid power**
- Assumes **positive = import**, **negative = export**
- Splits this into:
  - `grid_import_power` (W)
  - `grid_export_power` (W)

If your sign convention is reversed, we can flip it in a follow-up revision.
