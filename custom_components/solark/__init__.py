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
    CONF_AUTO_DISCOVER_API,
    CONF_SCAN_INTERVAL,
    CONF_ALLOW_WRITE,
    DEFAULT_BASE_URL,
    DEFAULT_API_URL,
    DEFAULT_AUTO_DISCOVER_API,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_ALLOW_WRITE,
    PLATFORMS,
    normalize_solark_urls,
)
from .discovery import discover_api_url

_LOGGER = logging.getLogger(__name__)

# Raise a repair issue once a SolArk sub-fetch has been failing this long.
FETCH_FAILURE_THRESHOLD_SECONDS = 3600  # 1 hour

# Human-friendly labels for the repair-issue {component} placeholder.
_FETCH_COMPONENT_LABELS: dict[str, str] = {
    "flow": "live flow data (PV, battery, grid and load power)",
    "workdata": "inverter work data (AC Relay Status)",
}


def _update_fetch_health_issues(
    hass: HomeAssistant, entry_id: str, api: Any
) -> None:
    """Create or clear repair issues based on per-sub-fetch health.

    Raises one repair issue per component that has been failing longer than
    FETCH_FAILURE_THRESHOLD_SECONDS and clears it as soon as the component
    recovers. Issue IDs are stable (one per entry and component) so there is
    never more than one issue per component, they auto-resolve on recovery,
    and one entry's recovery cannot clear another entry's issue.
    """
    from homeassistant.helpers import issue_registry as ir

    for component, failing_seconds in api.get_fetch_health().items():
        issue_id = f"fetch_failure_{entry_id}_{component}"
        if failing_seconds >= FETCH_FAILURE_THRESHOLD_SECONDS:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="fetch_failure",
                translation_placeholders={
                    "component": _FETCH_COMPONENT_LABELS.get(component, component),
                },
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up from YAML (not used)."""
    return True


async def _resolve_urls(hass: HomeAssistant, entry: ConfigEntry) -> tuple[str, str, bool]:
    """Normalize hosts and optionally rediscover the API base URL."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    api_url = entry.data.get(CONF_API_URL, DEFAULT_API_URL)
    auto_discover = entry.options.get(
        CONF_AUTO_DISCOVER_API,
        entry.data.get(CONF_AUTO_DISCOVER_API, DEFAULT_AUTO_DISCOVER_API),
    )
    base_url, api_url = normalize_solark_urls(base_url, api_url)

    if auto_discover:
        session = async_get_clientsession(hass)
        discovered = await discover_api_url(session, base_url)
        if discovered:
            api_url = discovered
        else:
            _LOGGER.warning(
                "SolArk API auto-discovery failed; using %s",
                api_url,
            )

    return base_url, api_url, bool(auto_discover)


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
    base_url, api_url, auto_discover = await _resolve_urls(hass, entry)

    # Persist resolved hosts / discovery flag so the UI and diagnostics stay
    # current. Safe to do here: the update listener is not registered until the
    # end of this function, so this cannot trigger a reload loop.
    new_data = {
        **entry.data,
        CONF_BASE_URL: base_url,
        CONF_API_URL: api_url,
        CONF_AUTO_DISCOVER_API: auto_discover,
    }
    if dict(entry.data) != new_data:
        _LOGGER.info(
            "Updating SolArk URLs for entry %s to base_url=%s api_url=%s auto_discover=%s",
            entry.entry_id,
            base_url,
            api_url,
            auto_discover,
        )
        hass.config_entries.async_update_entry(entry, data=new_data)

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
        "Setting up SolArk entry %s with scan_interval=%s seconds base_url=%s api_url=%s",
        entry.entry_id,
        scan_interval,
        base_url,
        api_url,
    )

    session = async_get_clientsession(hass)
    api = SolArkCloudAPI(
        username=username,
        password=password,
        plant_id=plant_id,
        base_url=base_url,
        api_url=api_url,
        session=session,
        timezone=hass.config.time_zone,
    )
    # Warm the inverter-list cache. Best effort only: the cache is lazy and
    # refetches on next use, so a cloud hiccup during HA startup must not
    # abort setup (an unhandled error here would leave the entry failed with
    # no retry).
    try:
        await api.prime_inverters_cache()
    except SolArkCloudAPIError as err:
        _LOGGER.warning(
            "Could not prefetch the inverter list (will retry on demand): %s",
            err,
        )

    async def async_update_data() -> dict[str, Any]:
        """Fetch and parse data from SolArk."""
        try:
            raw = await api.get_plant_data()
            parsed = api.parse_plant_data(raw)
        except SolArkCloudAPIError as err:
            raise UpdateFailed(str(err)) from err
        finally:
            # get_plant_data swallows per-sub-fetch errors (and raises only
            # when every fetch failed), so evaluate health on both outcomes
            # to raise/clear repair issues for prolonged failures.
            _update_fetch_health_issues(hass, entry.entry_id, api)
        return parsed

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
    # Settings are optional: some accounts can read telemetry but not inverter
    # settings (limited/installer logins), and some plants report no master
    # inverter. Failing here would take down every sensor, so refresh without
    # raising — the config sensors stay unavailable until a poll succeeds.
    await settings_coordinator.async_refresh()
    if not settings_coordinator.last_update_success:
        _LOGGER.warning(
            "Inverter settings are unavailable; configuration sensors will "
            "remain unavailable until a settings poll succeeds"
        )

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
    from homeassistant.core import ServiceCall
    from homeassistant.exceptions import HomeAssistantError

    from .services import CONFIGURE_INVERTER_SCHEMA, build_api_updates

    async def handle_configure_inverter(call: ServiceCall) -> None:
        """Handle the configure_inverter service call.

        Everything is resolved from hass.data at call time: a closure over
        this entry's objects would keep serving a stale api/allow-write
        snapshot after an options reload, and would KeyError after the entry
        is removed.
        """
        entry_data = next(iter(hass.data.get(DOMAIN, {}).values()), None)
        if not entry_data:
            raise HomeAssistantError("SolArk is not set up.")

        if not entry_data.get("allow_write_access"):
            raise HomeAssistantError("Write access is disabled for SolArk.")

        svc_api = entry_data["api"]
        svc_settings_coordinator = entry_data["settings_coordinator"]

        # Get master inverter SN from settings coordinator
        settings_data = svc_settings_coordinator.data or {}
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
            await svc_api.set_common_settings(
                sn=sn, updates=updates, require_master=True
            )
        except Exception as err:
            raise HomeAssistantError(f"Failed to configure inverter: {err}") from err

        # Trigger settings refresh
        refresh_burst = entry_data.get("settings_refresh_burst")
        if refresh_burst:
            await refresh_burst()
        await svc_settings_coordinator.async_request_refresh()

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
        stored = hass.data[DOMAIN].pop(entry.entry_id, None)
        if stored:
            task = stored.get("settings_refresh_task")
            if task and not task.done():
                task.cancel()
        # Clear any outstanding health repair issues for this entry.
        from homeassistant.helpers import issue_registry as ir

        for component in _FETCH_COMPONENT_LABELS:
            ir.async_delete_issue(
                hass, DOMAIN, f"fetch_failure_{entry.entry_id}_{component}"
            )
        # Last entry gone: the service has nothing left to act on.
        if not hass.data[DOMAIN] and hass.services.has_service(
            DOMAIN, "configure_inverter"
        ):
            hass.services.async_remove(DOMAIN, "configure_inverter")
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

    if version < 4:
        # v4: SolArk migrated accounts to the p2 cluster and moved the portal
        # off mysolark.com. The old api_url still serves reads but rejects all
        # settings writes (HTTP 500 / code=1). Repoint any entry still on a
        # retired host at the current defaults.
        old_base_url = data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
        old_api_url = data.get(CONF_API_URL, DEFAULT_API_URL)
        new_base_url, new_api_url = normalize_solark_urls(old_base_url, old_api_url)
        if (new_base_url, new_api_url) != (old_base_url, old_api_url):
            data[CONF_BASE_URL] = new_base_url
            data[CONF_API_URL] = new_api_url
            _LOGGER.info(
                "Migrated SolArk hosts: base_url %s -> %s, api_url %s -> %s",
                old_base_url,
                new_base_url,
                old_api_url,
                new_api_url,
            )
        version = 4

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
