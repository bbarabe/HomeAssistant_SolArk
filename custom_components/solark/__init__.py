"""SolArk integration entry point."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import SolArkCloudAPI, SolArkCloudAPIError

from pathlib import Path
import os


async def _ensure_dashboard_file(hass: HomeAssistant) -> None:
    """Ensure SolArk dashboard YAML is present in /config/dashboards.

    This will copy the bundled dashboards/solark_flow.yaml from the integration
    package into the Home Assistant config dashboards directory on first setup.
    It will NOT overwrite an existing file, so users can safely customize it.
    """
    try:
        dashboards_path = Path(hass.config.path("dashboards"))
        dashboards_path.mkdir(parents=True, exist_ok=True)
        target = dashboards_path / "solark_flow.yaml"

        # Do not clobber any user-customized dashboard.
        if target.exists():
            return

        src = Path(__file__).parent / "dashboards" / "solark_flow.yaml"
        if not src.exists():
            return

        target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("SolArk: Failed to ensure dashboard file: %s", err)


from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    CONF_BASE_URL,
    CONF_API_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_BASE_URL,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up from YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SolArk from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    plant_id = entry.data[CONF_PLANT_ID]
    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    api_url = entry.data.get(CONF_API_URL, DEFAULT_API_URL)

    scan_interval = int(
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    )

    _LOGGER.debug(
        "Setting up SolArk entry %s with scan_interval=%s seconds",
        entry.entry_id,
        scan_interval,
    )

    session = async_get_clientsession(hass)
    api = SolArkCloudAPI(
        username=username,
        password=password,
        plant_id=plant_id,
        base_url=base_url,
        api_url=api_url,
        session=session,
    )

    async def async_update_data() -> dict[str, Any]:
        """Fetch and parse data from SolArk."""
        try:
            raw = await api.get_plant_data()
            parsed = api.parse_plant_data(raw)
            return parsed
        except SolArkCloudAPIError as err:
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"SolArk {plant_id}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _ensure_dashboard_file(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        try:
            dashboards_path = Path(hass.config.path("dashboards"))
            target = dashboards_path / "solark_flow.yaml"
            if target.exists():
                target.unlink()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("SolArk: Failed to remove dashboard file: %s", err)
    return unload_ok
