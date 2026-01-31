"""Sol-Ark Cloud API client (Home Assistant independent)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

from .solark_auth import SolArkAuth
from .solark_errors import SolArkCloudAPIError
from .solark_logging import get_logger

_LOGGER = get_logger(__name__)


class SolArkCloudAPI:
    """Sol-Ark Cloud API client."""

    def __init__(
        self,
        username: str,
        password: str,
        plant_id: str,
        base_url: str,
        api_url: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self.username = username
        self.password = password
        self.plant_id = plant_id

        self.base_url = base_url.rstrip("/")
        self.api_url = api_url.rstrip("/")

        self._session = session
        self._master_sn: Optional[str] = None
        self._pending_setting_overrides: Dict[str, tuple[Any, datetime]] = {}
        self._pending_setting_ttl_seconds = 30
        self._inverters_cache: Optional[list[dict[str, Any]]] = None
        self._inverters_cache_lock = asyncio.Lock()
        self._auth = SolArkAuth(
            username=username,
            password=password,
            base_url=self.base_url,
            api_url=self.api_url,
            session=session,
        )

        _LOGGER.debug(
            "SolArkCloudAPI initialized for plant_id=%s, base_url=%s, api_url=%s",
            self.plant_id,
            self.base_url,
            self.api_url,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def prime_inverters_cache(self) -> None:
        """Fetch and cache inverter list once at startup."""
        await self._get_cached_inverters()

    async def _get_cached_inverters(self) -> list[dict[str, Any]]:
        if self._inverters_cache is not None:
            return self._inverters_cache

        async with self._inverters_cache_lock:
            if self._inverters_cache is not None:
                return self._inverters_cache

            inv_params = {
                "page": 1,
                "limit": 50,
                "stationId": self.plant_id,
                "status": -1,
                "sn": "",
                "type": -2,
            }
            _LOGGER.debug(
                "Requesting inverter list for cache with params=%s", inv_params
            )
            inv_resp = await self._request(
                "GET",
                f"/api/v1/plant/{self.plant_id}/inverters",
                inv_params,
            )
            inv_data = inv_resp.get("data") if isinstance(inv_resp, dict) else None
            inverters = []
            if isinstance(inv_data, dict):
                inverters = (
                    inv_data.get("infos")
                    or inv_data.get("list")
                    or inv_data.get("records")
                    or []
                )

            self._inverters_cache = inverters
            _LOGGER.debug(
                "Cached inverter list length: %s", len(self._inverters_cache)
            )
            return self._inverters_cache

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        auth_required: bool = True,
    ) -> Dict[str, Any]:
        if auth_required:
            await self._auth.ensure_token()

        url = f"{self.api_url}{endpoint}"
        headers = self._auth.get_headers(strict=True)

        json_body = None
        params = None
        if method.upper() in ("GET", "DELETE"):
            params = data
        else:
            json_body = data

        _LOGGER.debug(
            "Requesting %s %s with params=%s json=%s",
            method,
            url,
            params,
            json_body,
        )

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                text = await resp.text()
                _LOGGER.debug(
                    "Response %s %s -> HTTP %s, body: %s",
                    method,
                    url,
                    resp.status,
                    text[:1000],
                )
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError as exc:
                    raise SolArkCloudAPIError(
                        f"HTTP {resp.status} for {endpoint}: {text[:500]}"
                    ) from exc

                try:
                    result = await resp.json()
                except Exception as exc:  # noqa: BLE001
                    raise SolArkCloudAPIError(
                        f"Invalid JSON response from {endpoint}: {text[:200]}"
                    ) from exc

        except asyncio.TimeoutError as exc:  # noqa: BLE001
            raise SolArkCloudAPIError(f"Timeout for {endpoint}") from exc
        except aiohttp.ClientError as exc:  # noqa: BLE001
            raise SolArkCloudAPIError(f"Client error for {endpoint}: {exc}") from exc

        if isinstance(result, dict):
            code = result.get("code")
            if code not in (0, "0", None):
                msg = result.get("msg", "Unknown error")
                raise SolArkCloudAPIError(
                    f"API error for {endpoint}: {msg} (code={code})"
                )

        return result

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------

    async def login(self) -> bool:
        return await self._auth.login()

    # ------------------------------------------------------------------
    # plant data
    # ------------------------------------------------------------------

    async def get_inverter_live_data(self) -> Dict[str, Any]:
        """Fetch live inverter data via dy/store/{sn}/read."""
        await self._auth.ensure_token()
        _LOGGER.debug("Using cached inverter list for plant_id=%s", self.plant_id)
        inverters = await self._get_cached_inverters()
        _LOGGER.debug("Parsed inverters list length: %s", len(inverters))

        if not inverters:
            _LOGGER.warning("No inverters found for plant %s", self.plant_id)
            return {}

        first = inverters[0]
        _LOGGER.debug("First inverter entry: %s", first)
        sn = first.get("sn") or first.get("deviceSn")
        if not sn:
            _LOGGER.warning("First inverter for plant %s has no SN", self.plant_id)
            return {}

        live_data = await self.get_inverter_live_data_by_sn(sn)

        # Merge energy data from inverter summary into live_data
        try:
            etoday = first.get("etoday")
            etotal = first.get("etotal")
            if etoday is not None:
                live_data.setdefault("energyToday", etoday)
            if etotal is not None:
                live_data.setdefault("energyTotal", etotal)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug(
                "Unable to merge inverter energy stats into live data: %s", exc
            )

        return live_data

    async def get_inverter_live_data_by_sn(self, sn: str) -> Dict[str, Any]:
        """Fetch live inverter data via dy/store/{sn}/read for a specific inverter."""
        await self._auth.ensure_token()
        _LOGGER.debug("Requesting live data for inverter SN=%s", sn)
        live_resp = await self._request(
            "GET",
            f"/api/v1/dy/store/{sn}/read",
            {"sn": sn},
        )
        _LOGGER.debug("Raw live response: %s", live_resp)

        live_data = live_resp.get("data") or live_resp
        if not isinstance(live_data, dict):
            _LOGGER.debug("Live data for SN=%s is not a dict: %r", sn, live_data)
            return {}

        _LOGGER.debug("Live data keys for SN=%s: %s", sn, list(live_data.keys()))
        return live_data

    async def get_inverters(
        self,
        page: int = 1,
        limit: int = 10,
        total: int = 0,
        layout: str = "sizes,prev,+pager,+next,+jumper",
        status: int = -1,
        sn: str = "",
        plant_id: Optional[str] = None,
        inv_type: int = -2,
        soft_ver: str = "",
        hmi_ver: str = "",
        agent_company_id: int = -1,
        gsn: str = "",
    ) -> Dict[str, Any]:
        """Fetch inverter list using the /api/v1/inverters endpoint."""
        await self._auth.ensure_token()
        params = {
            "page": page,
            "limit": limit,
            "total": total,
            "layout": layout,
            "status": status,
            "sn": sn,
            "plantId": plant_id if plant_id is not None else "",
            "type": inv_type,
            "softVer": soft_ver,
            "hmiVer": hmi_ver,
            "agentCompanyId": agent_company_id,
            "gsn": gsn,
        }
        return await self._request("GET", "/api/v1/inverters", params)

    async def get_plants(
        self,
        page: int = 1,
        limit: int = 10,
        name: str = "",
        status: str = "",
        plant_type: int = -1,
        sort_col: str = "createAt",
        order: int = 2,
    ) -> Dict[str, Any]:
        """Fetch plants list via /api/v1/plants."""
        await self._auth.ensure_token()
        params = {
            "page": page,
            "limit": limit,
            "name": name,
            "status": status,
            "type": plant_type,
            "sortCol": sort_col,
            "order": order,
        }
        return await self._request("GET", "/api/v1/plants", params)

    async def get_gateways(
        self,
        page: int = 1,
        limit: int = 10,
        status: int = -1,
        sn: str = "",
        plant_id: Optional[str] = None,
        soft_ver: str = "",
        hard_ver: str = "",
        inv_sn: str = "",
        protocol: int = -1,
        agent_company_id: int = -1,
        lan: str = "en",
    ) -> Dict[str, Any]:
        """Fetch gateways list via /api/v1/gateways."""
        await self._auth.ensure_token()
        params = {
            "page": page,
            "limit": limit,
            "status": status,
            "sn": sn,
            "plantId": plant_id if plant_id is not None else "",
            "softVer": soft_ver,
            "hardVer": hard_ver,
            "invSn": inv_sn,
            "protocol": protocol,
            "agentCompanyId": agent_company_id,
            "lan": lan,
        }
        return await self._request("GET", "/api/v1/gateways", params)

    async def get_common_settings(self, sn: str) -> Dict[str, Any]:
        """Fetch common inverter settings via /api/v1/common/setting/{sn}/read."""
        await self._auth.ensure_token()
        response = await self._request("GET", f"/api/v1/common/setting/{sn}/read")
        return self._apply_pending_settings_to_response(response)

    async def get_master_common_settings(
        self, force_refresh: bool = False
    ) -> tuple[str, Dict[str, Any]]:
        """Fetch common settings for the master inverter.

        If a plant only has a single inverter and it is not marked as master,
        fall back to that inverter so settings can still be read.
        """
        cached_candidate: tuple[str, Dict[str, Any]] | None = None
        if self._master_sn and not force_refresh:
            settings_resp = await self.get_common_settings(self._master_sn)
            settings_data = (
                settings_resp.get("data")
                if isinstance(settings_resp, dict)
                else settings_resp
            )
            if isinstance(settings_data, dict):
                if settings_data.get("equipMode") == 1:
                    return self._master_sn, settings_data
                cached_candidate = (self._master_sn, settings_data)
            self._master_sn = None

        inverters = await self._get_cached_inverters()
        if not inverters:
            raise SolArkCloudAPIError("No inverters found for plant")

        valid_sns: list[str] = []
        fallback_candidate: tuple[str, Dict[str, Any]] | None = cached_candidate

        for inverter in inverters:
            sn = inverter.get("sn") or inverter.get("deviceSn")
            if not sn:
                continue
            valid_sns.append(sn)
            settings_resp = await self.get_common_settings(sn)
            settings_data = (
                settings_resp.get("data")
                if isinstance(settings_resp, dict)
                else settings_resp
            )
            if not isinstance(settings_data, dict):
                continue
            if settings_data.get("equipMode") == 1:
                self._master_sn = sn
                return sn, settings_data
            if fallback_candidate is None:
                fallback_candidate = (sn, settings_data)

        if len(valid_sns) == 1 and fallback_candidate is not None:
            sn, settings_data = fallback_candidate
            self._master_sn = sn
            _LOGGER.warning(
                "Master inverter not found (equipMode != 1); using sole inverter %s for settings",
                sn,
            )
            return sn, settings_data

        raise SolArkCloudAPIError("Master inverter not found (equipMode != 1)")

    async def set_common_settings(
        self,
        sn: str,
        updates: Dict[str, Any],
        require_master: bool = True,
    ) -> Dict[str, Any]:
        """Update common inverter settings using /api/v1/common/setting/{sn}/set."""
        settings_resp = await self.get_common_settings(sn)
        settings_data = (
            settings_resp.get("data")
            if isinstance(settings_resp, dict)
            else settings_resp
        )
        if not isinstance(settings_data, dict):
            raise SolArkCloudAPIError("Invalid settings response")

        if require_master:
            equip_mode = settings_data.get("equipMode")
            if equip_mode != 1:
                if not await self._allow_single_inverter_write(sn):
                    raise SolArkCloudAPIError(
                        f"Inverter {sn} is not master (equipMode={equip_mode})"
                    )

        payload = self._build_common_setting_payload(sn, settings_data)
        payload.update(updates)
        result = await self._request(
            "POST", f"/api/v1/common/setting/{sn}/set", payload
        )
        self._record_pending_settings(updates, settings_data)
        return result

    async def set_system_work_mode_slot(
        self,
        sn: str,
        slot: int,
        sell_time: Optional[str] = None,
        sell_pac: Optional[float] = None,
        sell_volt: Optional[float] = None,
        cap: Optional[float] = None,
        enabled: Optional[bool] = None,
        slot_mode: Optional[int] = None,
        gen_enabled: Optional[bool] = None,
        sys_work_mode: Optional[int] = None,
        require_master: bool = True,
    ) -> Dict[str, Any]:
        """Update a system work mode time slot for an inverter."""
        if slot not in (1, 2, 3, 4, 5, 6):
            raise ValueError("slot must be between 1 and 6")

        settings_resp = await self.get_common_settings(sn)
        settings_data = (
            settings_resp.get("data")
            if isinstance(settings_resp, dict)
            else settings_resp
        )
        if not isinstance(settings_data, dict):
            raise SolArkCloudAPIError("Invalid settings response")

        if require_master:
            equip_mode = settings_data.get("equipMode")
            if equip_mode != 1:
                if not await self._allow_single_inverter_write(sn):
                    raise SolArkCloudAPIError(
                        f"Inverter {sn} is not master (equipMode={equip_mode})"
                    )

        payload = self._build_common_setting_payload(sn, settings_data)

        updates: Dict[str, Any] = {}
        if sys_work_mode is not None:
            payload["sysWorkMode"] = sys_work_mode
            updates["sysWorkMode"] = sys_work_mode
        if sell_time is not None:
            payload[f"sellTime{slot}"] = sell_time
            updates[f"sellTime{slot}"] = sell_time
        if sell_pac is not None:
            payload[f"sellTime{slot}Pac"] = sell_pac
            updates[f"sellTime{slot}Pac"] = sell_pac
        if sell_volt is not None:
            payload[f"sellTime{slot}Volt"] = sell_volt
            updates[f"sellTime{slot}Volt"] = sell_volt
        if cap is not None:
            payload[f"cap{slot}"] = cap
            updates[f"cap{slot}"] = cap
        if enabled is not None:
            payload[f"time{slot}on"] = enabled
            updates[f"time{slot}on"] = enabled
        if gen_enabled is not None:
            payload[f"genTime{slot}on"] = gen_enabled
            updates[f"genTime{slot}on"] = gen_enabled
        if slot_mode is not None:
            # Map mode to sell/charge toggles (SolArk API uses timeXon for charge,
            # genTimeXon for sell).
            enabled = slot_mode in (2, 3)
            gen_enabled = slot_mode in (1, 3)
            payload[f"time{slot}on"] = enabled
            payload[f"genTime{slot}on"] = gen_enabled
            updates[f"time{slot}on"] = enabled
            updates[f"genTime{slot}on"] = gen_enabled

        result = await self._request(
            "POST", f"/api/v1/common/setting/{sn}/set", payload
        )
        if updates:
            self._record_pending_settings(updates, settings_data)
        return result

    async def _allow_single_inverter_write(self, sn: str) -> bool:
        """Allow writes when the plant only has a single inverter."""
        inverters = await self._get_cached_inverters()
        if not inverters:
            return False

        valid_sns = [inv.get("sn") or inv.get("deviceSn") for inv in inverters]
        valid_sns = [inv_sn for inv_sn in valid_sns if inv_sn]

        if len(inverters) == 1 and len(valid_sns) == 1 and valid_sns[0] == sn:
            _LOGGER.warning(
                "Allowing write to sole inverter %s despite equipMode != 1",
                sn,
            )
            return True

        return False

    async def get_flow_data(self) -> Dict[str, Any]:
        """Fetch plant power flow data (pv, batt, grid, load, soc)."""
        await self._auth.ensure_token()
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        params = {"date": date_str}
        endpoint = f"/api/v1/plant/energy/{self.plant_id}/flow"
        _LOGGER.debug(
            "Requesting energy flow for plant %s with params=%s",
            self.plant_id,
            params,
        )
        try:
            flow_resp = await self._request(
                "GET",
                endpoint,
                params,
            )
        except SolArkCloudAPIError as exc:  # noqa: BLE001
            _LOGGER.warning("Energy flow request failed: %s", exc)
            return {}

        _LOGGER.debug("Raw flow response: %s", flow_resp)
        flow_data = flow_resp.get("data") if isinstance(flow_resp, dict) else None
        if isinstance(flow_data, dict):
            return flow_data
        if isinstance(flow_resp, dict):
            return flow_resp
        return {}

    async def get_plant_data(
        self,
        live_data: Optional[Dict[str, Any]] = None,
        flow_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fetch combined plant data: inverter live + power flow."""
        # Start with inverter live data
        if live_data is None:
            live_data = await self.get_inverter_live_data()

        # Then overlay flow data (pvPower, battPower, gridOrMeterPower, loadOrEpsPower, soc)
        try:
            if flow_data is None:
                flow_data = await self.get_flow_data()
            if flow_data:
                _LOGGER.debug(
                    "Merging flow_data keys into live_data: %s", list(flow_data.keys())
                )
                for key, value in flow_data.items():
                    if key in (
                        "pvPower",
                        "battPower",
                        "gridOrMeterPower",
                        "loadOrEpsPower",
                        "soc",
                        "gridTo",
                        "toGrid",
                        "toBat",
                        "batTo",
                        "existsMeter",
                        "genOn",
                    ):
                        live_data[key] = value
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Unable to merge flow data into live data: %s", exc)

        return live_data

    async def test_connection(self) -> bool:
        try:
            await self.login()
            await self.get_plant_data()
            return True
        except SolArkCloudAPIError as exc:
            _LOGGER.error("SolArk test_connection failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # parsing helpers
    # ------------------------------------------------------------------

    def _safe_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def parse_plant_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map combined API fields to sensor values."""
        if not isinstance(data, dict):
            _LOGGER.warning("parse_plant_data got non-dict: %r", data)
            return {}

        _LOGGER.debug("parse_plant_data received keys: %s", list(data.keys()))

        sensors: Dict[str, Any] = {}

        # ----- Energy today / total -----
        if "energyToday" in data or "etoday" in data:
            sensors["energy_today"] = self._safe_float(
                data.get("energyToday", data.get("etoday"))
            )
        if "energyTotal" in data or "etotal" in data:
            sensors["energy_total"] = self._safe_float(
                data.get("energyTotal", data.get("etotal"))
            )

        # ----- Battery SOC -----
        if "soc" in data:
            sensors["battery_soc"] = self._safe_float(data.get("soc"))

        if "battery_soc" not in sensors:
            cur_cap = self._safe_float(data.get("curCap"))
            batt_cap = self._safe_float(data.get("batteryCap"))
            if batt_cap > 0:
                sensors["battery_soc"] = (cur_cap / batt_cap) * 100.0

        # ----- PV power -----
        if "pvPower" in data:
            sensors["pv_power"] = self._safe_float(data.get("pvPower"))

        pv_sum = 0.0
        for i in range(1, 13):
            v_raw = data.get(f"volt{i}")
            c_raw = data.get(f"current{i}")
            if v_raw is None and c_raw is None:
                continue
            v = self._safe_float(v_raw)
            c = self._safe_float(c_raw)
            pv_sum += v * c

        if "pv_power" not in sensors and pv_sum != 0.0:
            sensors["pv_power"] = pv_sum

        # ----- Battery power -----
        if "battPower" in data:
            batt_power = abs(self._safe_float(data.get("battPower")))
            to_bat = data.get("toBat")
            bat_to = data.get("batTo")
            if to_bat and not bat_to:
                sensors["battery_power"] = -batt_power
            elif bat_to and not to_bat:
                sensors["battery_power"] = batt_power
            else:
                sensors["battery_power"] = batt_power

        if "battery_power" not in sensors:
            cur_volt = self._safe_float(data.get("curVolt"))
            charge_current = self._safe_float(data.get("chargeCurrent"))
            if cur_volt != 0.0 or charge_current != 0.0:
                sensors["battery_power"] = cur_volt * charge_current

        # ----- Battery charge/discharge split -----
        battery_power = self._safe_float(sensors.get("battery_power"))
        if battery_power > 0.0:
            sensors["battery_discharge_power"] = battery_power
            sensors["battery_charge_power"] = 0.0
        elif battery_power < 0.0:
            sensors["battery_discharge_power"] = 0.0
            sensors["battery_charge_power"] = abs(battery_power)
        else:
            sensors["battery_discharge_power"] = 0.0
            sensors["battery_charge_power"] = 0.0

        # ----- Grid / Meter power (flow) -----
        if "gridOrMeterPower" in data:
            sensors["grid_power"] = self._safe_float(data.get("gridOrMeterPower"))

        # ----- Load / EPS power (flow) -----
        if "loadOrEpsPower" in data:
            sensors["load_power"] = self._safe_float(data.get("loadOrEpsPower"))

        # ----- Grid import/export from meterA/B/C -----
        meter_a = self._safe_float(data.get("meterA"))
        meter_b = self._safe_float(data.get("meterB"))
        meter_c = self._safe_float(data.get("meterC"))
        grid_net = meter_a + meter_b + meter_c

        if grid_net != 0.0:
            if grid_net > 0:
                sensors["grid_import_power"] = grid_net
                sensors["grid_export_power"] = 0.0
            else:
                sensors["grid_import_power"] = 0.0
                sensors["grid_export_power"] = abs(grid_net)
        else:
            if "gridImportPower" in data:
                sensors["grid_import_power"] = self._safe_float(
                    data.get("gridImportPower")
                )
            if "gridExportPower" in data:
                sensors["grid_export_power"] = self._safe_float(
                    data.get("gridExportPower")
                )

            # No CT meters: use gridOrMeterPower + direction flags from flow data.
            if (
                sensors.get("grid_import_power", 0.0) == 0.0
                and sensors.get("grid_export_power", 0.0) == 0.0
            ):
                exists_meter = data.get("existsMeter")
                no_meter = exists_meter in (False, 0, "0", None)
                if no_meter:
                    grid_flow = self._safe_float(data.get("gridOrMeterPower"))
                    if grid_flow != 0.0:
                        grid_to = data.get("gridTo")
                        to_grid = data.get("toGrid")
                        if grid_to is True and to_grid is not True:
                            sensors["grid_import_power"] = abs(grid_flow)
                            sensors["grid_export_power"] = 0.0
                        elif to_grid is True and grid_to is not True:
                            sensors["grid_import_power"] = 0.0
                            sensors["grid_export_power"] = abs(grid_flow)
                        else:
                            if grid_flow > 0.0:
                                sensors["grid_import_power"] = abs(grid_flow)
                                sensors["grid_export_power"] = 0.0
                            elif grid_flow < 0.0:
                                sensors["grid_import_power"] = 0.0
                                sensors["grid_export_power"] = abs(grid_flow)

        # ----- Grid Status -----
        grid_to = data.get("gridTo")
        to_grid = data.get("toGrid")
        if grid_to is False and to_grid is False:
            sensors["grid_status"] = "Inactive"
        elif grid_to or to_grid:
            sensors["grid_status"] = "Active"

        # ----- Generator Status -----
        gen_on = data.get("genOn")
        if gen_on is not None:
            sensors["generator_status"] = "Running" if gen_on else "Off"

        sensors.setdefault("pv_power", 0.0)
        sensors.setdefault("battery_power", 0.0)
        sensors.setdefault("grid_power", 0.0)
        sensors.setdefault("load_power", 0.0)
        sensors.setdefault("grid_import_power", 0.0)
        sensors.setdefault("grid_export_power", 0.0)
        sensors.setdefault("battery_soc", 0.0)
        sensors.setdefault("energy_today", 0.0)
        sensors.setdefault("energy_total", 0.0)
        sensors.setdefault("grid_status", "Unknown")
        sensors.setdefault("generator_status", "Unknown")
        sensors.setdefault("battery_charge_power", 0.0)
        sensors.setdefault("battery_discharge_power", 0.0)

        _LOGGER.debug("Parsed sensors dict: %s", sensors)
        return sensors

    def _build_common_setting_payload(
        self, sn: str, live_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        keys = [
            "safetyType",
            "battMode",
            "solarSell",
            "pvMaxLimit",
            "energyMode",
            "peakAndVallery",
            "sysWorkMode",
            "sellTime1",
            "sellTime2",
            "sellTime3",
            "sellTime4",
            "sellTime5",
            "sellTime6",
            "sellTime1Pac",
            "sellTime2Pac",
            "sellTime3Pac",
            "sellTime4Pac",
            "sellTime5Pac",
            "sellTime6Pac",
            "cap1",
            "cap2",
            "cap3",
            "cap4",
            "cap5",
            "cap6",
            "sellTime1Volt",
            "sellTime2Volt",
            "sellTime3Volt",
            "sellTime4Volt",
            "sellTime5Volt",
            "sellTime6Volt",
            "zeroExportPower",
            "solarMaxSellPower",
            "mondayOn",
            "tuesdayOn",
            "wednesdayOn",
            "thursdayOn",
            "fridayOn",
            "saturdayOn",
            "sundayOn",
            "time1on",
            "time2on",
            "time3on",
            "time4on",
            "time5on",
            "time6on",
            "genTime1on",
            "genTime2on",
            "genTime3on",
            "genTime4on",
            "genTime5on",
            "genTime6on",
        ]
        payload: Dict[str, Any] = {"sn": sn}
        for key in keys:
            value = live_data.get(key)
            if value is not None:
                payload[key] = value
        return payload

    def _apply_pending_settings_to_response(
        self, response: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not isinstance(response, dict):
            return response

        settings_data = response.get("data")
        if not isinstance(settings_data, dict):
            return response

        merged = self._merge_pending_settings(settings_data, prune_on_success=True)
        if merged is settings_data:
            return response
        updated = dict(response)
        updated["data"] = merged
        return updated

    def _merge_pending_settings(
        self, settings_data: Dict[str, Any], prune_on_success: bool
    ) -> Dict[str, Any]:
        if not self._pending_setting_overrides:
            return settings_data

        now = datetime.utcnow()
        merged = dict(settings_data)
        for key, (value, timestamp) in list(self._pending_setting_overrides.items()):
            expired = (
                (now - timestamp).total_seconds() > self._pending_setting_ttl_seconds
            )
            if prune_on_success and expired:
                self._pending_setting_overrides.pop(key, None)
                continue
            if settings_data.get(key) == value:
                if prune_on_success:
                    self._pending_setting_overrides.pop(key, None)
                continue
            merged[key] = value
        return merged

    def _record_pending_settings(
        self, updates: Dict[str, Any], settings_data: Dict[str, Any]
    ) -> None:
        now = datetime.utcnow()
        for key, value in updates.items():
            if settings_data.get(key) == value:
                self._pending_setting_overrides.pop(key, None)
                continue
            self._pending_setting_overrides[key] = (value, now)

    def has_pending_settings(self) -> bool:
        return bool(self._pending_setting_overrides)
