"""Select entities for Daikin AirBase Hot Water."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DaikinAirBaseHotWaterConfigEntry
from .drive_programs import (
    drive_program_label,
    drive_program_options,
    drive_program_value,
)
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

    def __init__(self, coordinator) -> None:
        """Initialise the select."""
        super().__init__(coordinator, "drive_program")

    @property
    def options(self) -> list[str]:
        """Return user-facing drive program options."""
        return drive_program_options(self.coordinator.data)

    @property
    def current_option(self) -> str | None:
        """Return current selected drive program."""
        program = self.coordinator.data.drive_program
        if program is None:
            return None
        return drive_program_label(program, self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        """Select a drive program."""
        await self.coordinator.async_set_control(
            drive_program=drive_program_value(option, self.coordinator.data)
        )
