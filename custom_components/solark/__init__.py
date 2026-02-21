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
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError

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
from .services import CONFIGURE_INVERTER_SCHEMA, build_api_updates

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
    await api.prime_inverters_cache()

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

    # Register the configure_inverter service
    async def handle_configure_inverter(call: ServiceCall) -> None:
        """Handle the configure_inverter service call."""
        # Check write access
        if not allow_write_access:
            raise HomeAssistantError("Write access is disabled for SolArk.")

        # Get master inverter SN from settings coordinator
        settings_data = settings_coordinator.data or {}
        sn = settings_data.get("sn")
        if not sn:
            raise HomeAssistantError("Master inverter not available.")

        # Convert service parameters to API updates
        service_data = dict(call.data)

        # Handle time objects - convert to HH:MM strings
        for key, value in list(service_data.items()):
            if hasattr(value, "strftime"):
                service_data[key] = value.strftime("%H:%M")

        updates = build_api_updates(service_data)
        if not updates:
            _LOGGER.warning("No valid parameters provided to configure_inverter")
            return

        _LOGGER.info(
            "Configuring inverter %s with updates: %s",
            sn,
            list(updates.keys()),
        )

        try:
            await api.set_common_settings(sn=sn, updates=updates, require_master=True)
        except Exception as err:
            raise HomeAssistantError(f"Failed to configure inverter: {err}") from err

        # Trigger settings refresh
        refresh_burst = hass.data[DOMAIN][entry.entry_id].get("settings_refresh_burst")
        if refresh_burst:
            await refresh_burst()
        await settings_coordinator.async_request_refresh()

    # Only register service once (first entry)
    if not hass.services.has_service(DOMAIN, "configure_inverter"):
        hass.services.async_register(
            DOMAIN,
            "configure_inverter",
            handle_configure_inverter,
            schema=CONFIGURE_INVERTER_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries to the latest version."""
    from homeassistant.helpers import entity_registry as er

    version = entry.version
    data = dict(entry.data)
    options = dict(entry.options)

    if version < 2:
        if CONF_ALLOW_WRITE not in options:
            options[CONF_ALLOW_WRITE] = data.get(
                CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE
            )
        version = 2

    if version < 3:
        # v3: Removed number/switch/select/time platforms, replaced with
        # read-only config sensors + configure_inverter service.
        # Clean up orphaned entities from old platforms.
        ent_reg = er.async_get(hass)

        # Old unique_id patterns that need cleanup
        old_unique_ids = [
            # Number entities
            f"{entry.entry_id}_solarMaxSellPower",
            f"{entry.entry_id}_zeroExportPower",
            f"{entry.entry_id}_pvMaxLimit",
            # Switch entities
            f"{entry.entry_id}_solarSell",
            f"{entry.entry_id}_peakAndVallery",
            f"{entry.entry_id}_mondayOn",
            f"{entry.entry_id}_tuesdayOn",
            f"{entry.entry_id}_wednesdayOn",
            f"{entry.entry_id}_thursdayOn",
            f"{entry.entry_id}_fridayOn",
            f"{entry.entry_id}_saturdayOn",
            f"{entry.entry_id}_sundayOn",
            # Select entities
            f"{entry.entry_id}_sysWorkMode",
            f"{entry.entry_id}_energyMode",
        ]
        # Add slot-based entities (1-6)
        for i in range(1, 7):
            old_unique_ids.extend([
                f"{entry.entry_id}_sellTime{i}Pac",  # Number: slot power
                f"{entry.entry_id}_cap{i}",  # Number: slot SOC
                f"{entry.entry_id}_sellTime{i}",  # Time: slot time
                f"{entry.entry_id}_time{i}mode",  # Select: slot mode
            ])

        removed_count = 0
        for unique_id in old_unique_ids:
            entity_id = ent_reg.async_get_entity_id(
                "number", DOMAIN, unique_id
            ) or ent_reg.async_get_entity_id(
                "switch", DOMAIN, unique_id
            ) or ent_reg.async_get_entity_id(
                "select", DOMAIN, unique_id
            ) or ent_reg.async_get_entity_id(
                "time", DOMAIN, unique_id
            )
            if entity_id:
                ent_reg.async_remove(entity_id)
                removed_count += 1
                _LOGGER.debug("Removed orphaned entity: %s", entity_id)

        if removed_count:
            _LOGGER.info(
                "Cleaned up %d orphaned entities from old platforms", removed_count
            )
        version = 3

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
