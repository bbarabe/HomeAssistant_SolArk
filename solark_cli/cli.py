"""CLI tool to exercise the SolArk cloud client."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.solark.const import DEFAULT_API_URL, DEFAULT_BASE_URL


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SolArk Cloud CLI - test communication and auth.",
    )
    parser.add_argument(
        "--secrets",
        default=str((ROOT / "solark_secrets.json").resolve()),
        help="Path to secrets JSON file",
    )
    parser.add_argument("--username", help="SolArk account username")
    parser.add_argument("--password", help="SolArk account password")
    parser.add_argument("--plant-id", help="SolArk plant ID")
    parser.add_argument("--base-url", help="Base URL for the SolArk web app")
    parser.add_argument("--api-url", help="Base URL for the SolArk API")
    parser.add_argument(
        "--plants",
        action="store_true",
        help="Fetch plant list",
    )
    parser.add_argument(
        "--inverters",
        action="store_true",
        help="Fetch inverter list",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch inverter live data",
    )
    parser.add_argument(
        "--flow",
        action="store_true",
        help="Fetch plant flow data",
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        help="Fetch combined plant data",
    )
    parser.add_argument(
        "--parsed",
        action="store_true",
        help="Parse combined plant data into sensor values",
    )
    parser.add_argument(
        "--gateways",
        action="store_true",
        help="Fetch gateways list",
    )
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Fetch common settings for an inverter",
    )
    parser.add_argument(
        "--set-slot",
        action="store_true",
        help="Update a system work mode slot for an inverter",
    )
    parser.add_argument(
        "--inverter-sn",
        help="Inverter serial number for settings changes",
    )
    parser.add_argument(
        "--slot",
        type=int,
        help="Slot number (1-6)",
    )
    parser.add_argument(
        "--slot-time",
        help="Sell time for the slot (HH:MM)",
    )
    parser.add_argument(
        "--slot-pac",
        type=float,
        help="Sell power (PAC) for the slot",
    )
    parser.add_argument(
        "--slot-volt",
        type=float,
        help="Sell voltage for the slot",
    )
    parser.add_argument(
        "--slot-cap",
        type=float,
        help="Battery cap for the slot",
    )
    parser.add_argument(
        "--slot-mode",
        choices=["sell", "charge"],
        help="Slot mode (sell or charge)",
    )
    parser.add_argument(
        "--sys-work-mode",
        type=int,
        help="System work mode value (e.g., 1 for sell)",
    )
    parser.add_argument(
        "--allow-non-master",
        action="store_true",
        help="Allow setting changes on non-master inverters",
    )
    return parser


def _print_section(title: str, payload: object) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _load_secrets(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to read secrets file {path}: {exc}", file=sys.stderr)
        return {}


def _parse_slot_mode(value: str | None) -> int | None:
    if value is None:
        return None
    mapping = {"sell": 1, "charge": 2}
    return mapping[value]


async def _run(args: argparse.Namespace) -> int:
    try:
        import aiohttp
    except ModuleNotFoundError as exc:
        print(
            "Missing dependency: aiohttp. Install it before running this CLI.",
            file=sys.stderr,
        )
        return 1

    from custom_components.solark.solark_client import SolArkCloudAPI
    from custom_components.solark.solark_errors import SolArkCloudAPIError

    secrets = {}
    if not (args.username and args.password and args.plant_id):
        secrets = _load_secrets(args.secrets)

    username = args.username or secrets.get("username")
    password = args.password or secrets.get("password")
    plant_id = args.plant_id or secrets.get("plant_id")
    base_url = args.base_url or secrets.get("base_url") or DEFAULT_BASE_URL
    api_url = args.api_url or secrets.get("api_url") or DEFAULT_API_URL

    requested = {
        "plants": args.plants,
        "inverters": args.inverters,
        "live": args.live,
        "flow": args.flow,
        "combined": args.combined,
        "parsed": args.parsed,
        "gateways": args.gateways,
        "settings": args.settings,
    }
    if not any(requested.values()) and not args.set_slot:
        for key in requested:
            requested[key] = True

    requires_plant_id = any(
        [
            requested["flow"],
            requested["combined"],
            requested["parsed"],
            (requested["live"] and not args.inverter_sn),
        ]
    )

    required = [
        ("username", username),
        ("password", password),
    ]
    if requires_plant_id:
        required.append(("plant_id", plant_id))

    missing = [name for name, value in required if not value]
    if missing:
        print(
            "Missing required values: "
            + ", ".join(missing)
            + ". Provide CLI args or a secrets file.",
            file=sys.stderr,
        )
        return 2

    async with aiohttp.ClientSession() as session:
        client = SolArkCloudAPI(
            username=username,
            password=password,
            plant_id=plant_id,
            base_url=base_url,
            api_url=api_url,
            session=session,
        )

        try:
            await client.login()
        except SolArkCloudAPIError as exc:
            print(f"Login failed: {exc}", file=sys.stderr)
            return 1

        try:
            live_data = None
            flow_data = None
            combined = None

            if args.set_slot:
                if not args.inverter_sn or args.slot is None:
                    print(
                        "Missing --inverter-sn or --slot for --set-slot.",
                        file=sys.stderr,
                    )
                    return 2
                set_result = await client.set_system_work_mode_slot(
                    sn=args.inverter_sn,
                    slot=args.slot,
                    sell_time=args.slot_time,
                    sell_pac=args.slot_pac,
                    sell_volt=args.slot_volt,
                    cap=args.slot_cap,
                    slot_mode=_parse_slot_mode(args.slot_mode),
                    sys_work_mode=args.sys_work_mode,
                    require_master=not args.allow_non_master,
                )
                _print_section("Set Slot Result", set_result)

            if requested["settings"]:
                if not args.inverter_sn:
                    print(
                        "Missing --inverter-sn for --settings.",
                        file=sys.stderr,
                    )
                    return 2
                settings = await client.get_common_settings(args.inverter_sn)
                _print_section("Common Settings", settings)

            if requested["plants"]:
                plants = await client.get_plants()
                _print_section("Plant List", plants)

            if requested["inverters"]:
                inverter_list = await client.get_inverters()
                _print_section("Inverter List", inverter_list)

            if requested["gateways"]:
                gateways = await client.get_gateways()
                _print_section("Gateway List", gateways)

            if requested["live"]:
                if args.inverter_sn:
                    live_data = await client.get_inverter_live_data_by_sn(
                        args.inverter_sn
                    )
                else:
                    live_data = await client.get_inverter_live_data()
                _print_section("Inverter Live Data", live_data)

            if requested["flow"]:
                flow_data = await client.get_flow_data()
                _print_section("Flow Data", flow_data)

            if requested["combined"]:
                combined = await client.get_plant_data(
                    live_data=live_data, flow_data=flow_data
                )
                _print_section("Combined Plant Data", combined)

            if requested["parsed"]:
                if combined is None:
                    combined = await client.get_plant_data(
                        live_data=live_data, flow_data=flow_data
                    )
                parsed = client.parse_plant_data(combined)
                _print_section("Parsed Sensor Values", parsed)
        except SolArkCloudAPIError as exc:
            print(f"API error: {exc}", file=sys.stderr)
            return 1

    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))
