"""Config flow for Daikin AirBase Hot Water."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import (
    AirBaseHotWaterConnectionError,
    AirBaseHotWaterResponseError,
    DaikinAirBaseHotWaterApi,
)
from .const import CONF_PORT, DEFAULT_PORT, DOMAIN


class CannotConnect(Exception):
    """Raised when the controller cannot be reached."""


class InvalidResponse(Exception):
    """Raised when the controller response is not valid for this integration."""


class DaikinAirBaseHotWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Daikin AirBase Hot Water config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            try:
                await _validate_input(self.hass, host, port)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Daikin hot water ({host})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )


async def _validate_input(hass: HomeAssistant, host: str, port: int) -> None:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    api = DaikinAirBaseHotWaterApi(host, session, port=port)
    try:
        await api.get_status()
    except AirBaseHotWaterConnectionError as exc:
        raise CannotConnect from exc
    except AirBaseHotWaterResponseError as exc:
        raise InvalidResponse from exc


def _schema(user_input: dict[str, Any] | None) -> vol.Schema:
    """Return the config form schema."""
    defaults = user_input or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Optional(
                CONF_PORT,
                default=defaults.get(CONF_PORT, DEFAULT_PORT),
            ): int,
        }
    )
