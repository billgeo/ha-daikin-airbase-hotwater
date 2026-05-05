"""Data update coordinator for Daikin AirBase Hot Water."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    AirBaseHotWaterDayPower,
    AirBaseHotWaterError,
    AirBaseHotWaterStatus,
    DaikinAirBaseHotWaterApi,
)
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN, ENERGY_SCAN_INTERVAL_SECONDS

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
        self.energy_data: AirBaseHotWaterDayPower | None = None
        self._last_energy_update: datetime | None = None

    async def _async_update_data(self) -> AirBaseHotWaterStatus:
        """Fetch latest state from the controller."""
        try:
            status = await self.api.get_status()
        except AirBaseHotWaterError as exc:
            raise UpdateFailed(str(exc)) from exc
        await self._async_maybe_update_energy_data()
        return status

    async def _async_maybe_update_energy_data(self) -> None:
        """Refresh energy data on a slower cadence than status data."""
        now = datetime.now(UTC)
        if (
            self._last_energy_update is not None
            and now - self._last_energy_update
            < timedelta(seconds=ENERGY_SCAN_INTERVAL_SECONDS)
        ):
            return

        self._last_energy_update = now
        try:
            self.energy_data = await self.api.get_day_power()
        except AirBaseHotWaterError as exc:
            _LOGGER.debug("Failed to update hot water energy data: %s", exc)

    async def async_set_control(self, **kwargs: object) -> None:
        """Write controls then refresh coordinator data."""
        await self.api.set_control(**kwargs)
        await self.async_request_refresh()
