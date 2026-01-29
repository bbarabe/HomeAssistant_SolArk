# SolArk Cloud CLI

This document describes the command-line interface located in `solark_cli/`.

## Overview

The CLI is a lightweight wrapper around the SolArk Cloud API client. It is
intended for quick diagnostics, testing credentials, and inspecting live and
flow data without Home Assistant.

Entry point:

```bash
python -m solark_cli
```

## Requirements

- Python 3.10+ (same baseline as the integration)
- `aiohttp` installed (the CLI will exit with an error if missing)

## Secrets File

The CLI can read credentials from a JSON file. A template exists in the repo:

- `solark_secrets.template.json` (safe to commit)

Copy it to `solark_secrets.json` and fill in your values:

```json
{
  "username": "your-email@example.com",
  "password": "your-password",
  "plant_id": "YOUR_PLANT_ID",
  "base_url": "https://www.mysolark.com",
  "api_url": "https://ecsprod-api-new.solarkcloud.com"
}
```

Default lookup path for secrets is `solark_secrets.json` in the repo root.

## Usage

```bash
python -m solark_cli [options]
```

If no action flags are provided, the CLI fetches everything it can:
plants, inverters, live data, flow data, combined data, parsed sensors,
gateways, and common settings (where possible).

## Options

Authentication and URLs:

- `--secrets PATH` - Path to secrets JSON file
- `--username USERNAME` - SolArk account username
- `--password PASSWORD` - SolArk account password
- `--plant-id PLANT_ID` - SolArk plant ID
- `--base-url BASE_URL` - Base URL for the SolArk web app
- `--api-url API_URL` - Base URL for the SolArk API

Data fetch actions:

- `--plants` - Fetch plant list
- `--inverters` - Fetch inverter list
- `--live` - Fetch inverter live data
- `--flow` - Fetch plant flow data
- `--combined` - Fetch combined plant data (live + flow)
- `--parsed` - Parse combined plant data into sensor values
- `--gateways` - Fetch gateways list
- `--settings` - Fetch common settings for an inverter

Settings updates:

- `--set-slot` - Update a system work mode slot for an inverter
- `--inverter-sn SN` - Inverter serial number for settings changes
- `--slot N` - Slot number (1-6)
- `--slot-time HH:MM` - Sell time for the slot
- `--slot-pac VALUE` - Sell power (PAC) for the slot
- `--slot-volt VALUE` - Sell voltage for the slot
- `--slot-cap VALUE` - Battery cap for the slot
- `--slot-mode sell|charge` - Slot mode
- `--sys-work-mode VALUE` - System work mode value (e.g., 1 for sell)
- `--allow-non-master` - Allow setting changes on non-master inverters

## Behavior Notes

- `--live` without `--inverter-sn` fetches the plant inverter list and uses
  the first inverter found.
- `--flow`, `--combined`, and `--parsed` require a valid `plant_id`.
- `--settings` and `--set-slot` require `--inverter-sn`.
- `--set-slot` requires `--inverter-sn` and `--slot`.
- Output is printed as JSON with sorted keys inside section headers.

## Examples

Fetch combined live + flow data and parsed sensors:

```bash
python -m solark_cli --secrets solark_secrets.json --combined --parsed
```

Fetch live data for a specific inverter:

```bash
python -m solark_cli --secrets solark_secrets.json --live --inverter-sn 2201064650
```

Fetch plant flow data only:

```bash
python -m solark_cli --secrets solark_secrets.json --flow
```

Update slot 2 to sell at 18:00 with 3000W:

```bash
python -m solark_cli \
  --secrets solark_secrets.json \
  --set-slot \
  --inverter-sn 2201064650 \
  --slot 2 \
  --slot-time 18:00 \
  --slot-pac 3000 \
  --slot-mode sell
```

## Exit Codes

- `0` - Success
- `1` - Login/API error or missing dependency (`aiohttp`)
- `2` - Missing required arguments (e.g., credentials or slot info)

## Troubleshooting

- **Missing dependency**: Install `aiohttp` in your environment.
- **Missing required values**: Provide required flags or a secrets file.
- **API error**: Verify credentials at mysolark.com and confirm your Plant ID.
- **No inverters found**: Ensure the Plant ID is correct and the account has
  access to at least one inverter.
