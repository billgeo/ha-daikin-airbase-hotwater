"""Daikin AirBase Hot Water integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DaikinAirBaseHotWaterApi
from .const import CONF_PORT, DEFAULT_PORT, DOMAIN, PLATFORMS
from .coordinator import (
    DaikinAirBaseHotWaterConfigEntry,
    DaikinAirBaseHotWaterCoordinator,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DaikinAirBaseHotWaterConfigEntry,
) -> bool:
    """Set up Daikin AirBase Hot Water from a config entry."""
    session = async_get_clientsession(hass)
    api = DaikinAirBaseHotWaterApi(
        entry.data[CONF_HOST],
        session,
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
    )
    coordinator = DaikinAirBaseHotWaterCoordinator(hass, entry, api)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: DaikinAirBaseHotWaterConfigEntry,
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
