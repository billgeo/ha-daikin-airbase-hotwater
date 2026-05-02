"""Select entities for Daikin AirBase Hot Water."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DRIVE_PROGRAM_LABELS
from .coordinator import DaikinAirBaseHotWaterConfigEntry
from .entity import DaikinAirBaseHotWaterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DaikinAirBaseHotWaterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    async_add_entities([DaikinAirBaseHotWaterDriveProgramSelect(entry.runtime_data)])


class DaikinAirBaseHotWaterDriveProgramSelect(
    DaikinAirBaseHotWaterEntity,
    SelectEntity,
):
    """Select control for the active drive program."""

    _attr_options = list(DRIVE_PROGRAM_LABELS.values())

    def __init__(self, coordinator) -> None:
        """Initialise the select."""
        super().__init__(coordinator, "drive_program")

    @property
    def current_option(self) -> str | None:
        """Return current selected drive program."""
        return self.coordinator.data.drive_program

    async def async_select_option(self, option: str) -> None:
        """Select a drive program."""
        await self.coordinator.async_set_control(drive_program=option)
