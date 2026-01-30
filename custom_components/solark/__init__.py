"""SolArk integration entry point."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    CONF_BASE_URL,
    CONF_API_URL,
    CONF_SCAN_INTERVAL,
    CONF_ALLOW_WRITE,
    DEFAULT_BASE_URL,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_ALLOW_WRITE,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up from YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SolArk from a config entry."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.update_coordinator import (
        DataUpdateCoordinator,
        UpdateFailed,
    )

    from .solark_client import SolArkCloudAPI
    from .solark_errors import SolArkCloudAPIError
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
    allow_write_access = bool(
        entry.options.get(
            CONF_ALLOW_WRITE,
            entry.data.get(CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE),
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

    async def async_update_settings() -> dict[str, Any]:
        """Fetch master inverter settings for configuration entities."""
        try:
            sn, settings = await api.get_master_common_settings()
            return {"sn": sn, "settings": settings}
        except SolArkCloudAPIError as err:
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"SolArk {plant_id}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )
    settings_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"SolArk {plant_id} Settings",
        update_method=async_update_settings,
        update_interval=timedelta(seconds=max(scan_interval, 300)),
    )

    await coordinator.async_config_entry_first_refresh()
    await settings_coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "settings_coordinator": settings_coordinator,
        "allow_write_access": allow_write_access,
        "settings_refresh_task": None,
    }
    hass.data[DOMAIN][entry.entry_id]["settings_refresh_burst"] = (
        _build_settings_refresh_burst(hass, entry.entry_id)
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries to the latest version."""
    version = entry.version
    data = dict(entry.data)
    options = dict(entry.options)

    if version < 2:
        if CONF_ALLOW_WRITE not in options:
            options[CONF_ALLOW_WRITE] = data.get(
                CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE
            )
        version = 2

    hass.config_entries.async_update_entry(
        entry, data=data, options=options, version=version
    )
    _LOGGER.info("Migrated SolArk config entry to v%s", version)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options updates."""
    await hass.config_entries.async_reload(entry.entry_id)


def _build_settings_refresh_burst(hass: HomeAssistant, entry_id: str):
    async def _async_settings_refresh_burst() -> None:
        data = hass.data[DOMAIN].get(entry_id)
        if not data:
            return
        task = data.get("settings_refresh_task")
        if task and not task.done():
            return

        async def _runner() -> None:
            api = data.get("api")
            settings_coordinator = data.get("settings_coordinator")
            if not api or not settings_coordinator:
                return
            for _ in range(4):
                await settings_coordinator.async_request_refresh()
                if not api.has_pending_settings():
                    break
                await asyncio.sleep(15)

        data["settings_refresh_task"] = hass.async_create_task(_runner())

    return _async_settings_refresh_burst
