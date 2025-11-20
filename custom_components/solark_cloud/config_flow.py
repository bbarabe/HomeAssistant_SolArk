"""Config flow for Sol-Ark Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .api import SolArkCloudAPI, SolArkCloudAPIError
from .const import (
    DOMAIN,
    CONF_PLANT_ID,
    CONF_BASE_URL,
    CONF_AUTH_MODE,
    CONF_SCAN_INTERVAL,
    DEFAULT_BASE_URL,
    DEFAULT_AUTH_MODE,
    DEFAULT_SCAN_INTERVAL,
    BASE_URL_OPTIONS,
    AUTH_MODE_OPTIONS,
    MIN_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = SolArkCloudAPI(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        plant_id=data[CONF_PLANT_ID],
        base_url=data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        auth_mode=data.get(CONF_AUTH_MODE, DEFAULT_AUTH_MODE),
    )

    async with api:
        if not await api.test_connection():
            raise SolArkCloudAPIError("Failed to connect to Sol-Ark Cloud")

    return {"title": f"Sol-Ark Plant {data[CONF_PLANT_ID]}"}


class SolArkCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sol-Ark Cloud."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Check for duplicate entries
                await self.async_set_unique_id(
                    f"{user_input[CONF_USERNAME]}_{user_input[CONF_PLANT_ID]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)
            except SolArkCloudAPIError as err:
                _LOGGER.error("Failed to connect: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        # Build the configuration form schema
        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.EMAIL,
                        autocomplete="email",
                    ),
                ),
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                        autocomplete="current-password",
                    ),
                ),
                vol.Required(CONF_PLANT_ID): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                    ),
                ),
                vol.Optional(
                    CONF_BASE_URL,
                    default=DEFAULT_BASE_URL,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=BASE_URL_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional(
                    CONF_AUTH_MODE,
                    default=DEFAULT_AUTH_MODE,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=AUTH_MODE_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=30,
                        unit_of_measurement="seconds",
                        mode=selector.NumberSelectorMode.BOX,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "base_url": DEFAULT_BASE_URL,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SolArkCloudOptionsFlow:
        """Get the options flow for this handler."""
        return SolArkCloudOptionsFlow(config_entry)


class SolArkCloudOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Sol-Ark Cloud."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the new settings if credentials changed
            if (
                CONF_USERNAME in user_input
                or CONF_PASSWORD in user_input
                or CONF_PLANT_ID in user_input
            ):
                try:
                    test_data = {
                        CONF_USERNAME: user_input.get(
                            CONF_USERNAME, self.config_entry.data[CONF_USERNAME]
                        ),
                        CONF_PASSWORD: user_input.get(
                            CONF_PASSWORD, self.config_entry.data[CONF_PASSWORD]
                        ),
                        CONF_PLANT_ID: user_input.get(
                            CONF_PLANT_ID, self.config_entry.data[CONF_PLANT_ID]
                        ),
                        CONF_BASE_URL: user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                        CONF_AUTH_MODE: user_input.get(CONF_AUTH_MODE, DEFAULT_AUTH_MODE),
                    }
                    await validate_input(self.hass, test_data)
                except SolArkCloudAPIError:
                    errors["base"] = "cannot_connect"
                except Exception:  # pylint: disable=broad-except
                    errors["base"] = "unknown"

            if not errors:
                # Update the config entry with new data
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **user_input},
                    options=user_input,
                )
                return self.async_create_entry(title="", data=user_input)

        # Build options schema with current values
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_BASE_URL,
                    default=self.config_entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=BASE_URL_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional(
                    CONF_AUTH_MODE,
                    default=self.config_entry.data.get(CONF_AUTH_MODE, DEFAULT_AUTH_MODE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=AUTH_MODE_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.data.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=30,
                        unit_of_measurement="seconds",
                        mode=selector.NumberSelectorMode.BOX,
                    ),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )
