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

    missing = [
        name
        for name, value in (
            ("username", username),
            ("password", password),
            ("plant_id", plant_id),
        )
        if not value
    ]
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
            live_data = await client.get_inverter_live_data()
            _print_section("Inverter Live Data", live_data)

            flow_data = await client.get_flow_data()
            _print_section("Flow Data", flow_data)

            combined = await client.get_plant_data(
                live_data=live_data, flow_data=flow_data
            )
            _print_section("Combined Plant Data", combined)

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
