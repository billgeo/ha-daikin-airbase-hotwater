"""Number entities for Daikin AirBase Hot Water."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AirBaseHotWaterStatus
from .coordinator import DaikinAirBaseHotWaterConfigEntry
from .entity import DaikinAirBaseHotWaterEntity


@dataclass(frozen=True, kw_only=True)
class AirBaseHotWaterNumberEntityDescription(NumberEntityDescription):
    """Description for a hot water number control."""

    value_fn: Callable[[AirBaseHotWaterStatus], int | None]
    control_key: str


NUMBERS: tuple[AirBaseHotWaterNumberEntityDescription, ...] = (
    AirBaseHotWaterNumberEntityDescription(
        key="boil_level",
        translation_key="boil_level",
        native_min_value=0,
        native_max_value=6,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda status: status.boil_level,
        control_key="boil_level",
    ),
    AirBaseHotWaterNumberEntityDescription(
        key="vacation_days",
        translation_key="vacation_days",
        native_min_value=0,
        native_max_value=365,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda status: status.vacation_days,
        control_key="vacation_days",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DaikinAirBaseHotWaterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    async_add_entities(
        DaikinAirBaseHotWaterNumber(entry.runtime_data, description)
        for description in NUMBERS
    )


class DaikinAirBaseHotWaterNumber(DaikinAirBaseHotWaterEntity, NumberEntity):
    """Number control for a hot water value."""

    entity_description: AirBaseHotWaterNumberEntityDescription

    def __init__(
        self,
        coordinator,
        description: AirBaseHotWaterNumberEntityDescription,
    ) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator, description.translation_key)
        self.entity_description = description

    @property
    def native_value(self) -> int | None:
        """Return current value."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        await self.coordinator.async_set_control(
            **{self.entity_description.control_key: int(value)}
        )
