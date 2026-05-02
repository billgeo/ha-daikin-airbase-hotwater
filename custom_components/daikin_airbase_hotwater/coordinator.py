"""Data update coordinator for Daikin AirBase Hot Water."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AirBaseHotWaterError, AirBaseHotWaterStatus, DaikinAirBaseHotWaterApi
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)

DaikinAirBaseHotWaterConfigEntry = ConfigEntry


class DaikinAirBaseHotWaterCoordinator(DataUpdateCoordinator[AirBaseHotWaterStatus]):
    """Coordinator for polling the hot water controller."""

    config_entry: DaikinAirBaseHotWaterConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: DaikinAirBaseHotWaterConfigEntry,
        api: DaikinAirBaseHotWaterApi,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.config_entry = entry
        self.api = api

    async def _async_update_data(self) -> AirBaseHotWaterStatus:
        """Fetch latest state from the controller."""
        try:
            return await self.api.get_status()
        except AirBaseHotWaterError as exc:
            raise UpdateFailed(str(exc)) from exc

    async def async_set_control(self, **kwargs: object) -> None:
        """Write controls then refresh coordinator data."""
        await self.api.set_control(**kwargs)
        await self.async_request_refresh()
