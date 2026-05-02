"""Switch entities for Daikin AirBase Hot Water."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AirBaseHotWaterStatus
from .coordinator import DaikinAirBaseHotWaterConfigEntry
from .entity import DaikinAirBaseHotWaterEntity


@dataclass(frozen=True, kw_only=True)
class AirBaseHotWaterSwitchEntityDescription(SwitchEntityDescription):
    """Description for a hot water switch."""

    value_fn: Callable[[AirBaseHotWaterStatus], bool | None]
    control_key: str


SWITCHES: tuple[AirBaseHotWaterSwitchEntityDescription, ...] = (
    AirBaseHotWaterSwitchEntityDescription(
        key="boost",
        translation_key="boost",
        value_fn=lambda status: status.boost,
        control_key="boost",
    ),
    AirBaseHotWaterSwitchEntityDescription(
        key="vacation",
        translation_key="vacation",
        value_fn=lambda status: status.vacation,
        control_key="vacation",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DaikinAirBaseHotWaterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    async_add_entities(
        DaikinAirBaseHotWaterSwitch(entry.runtime_data, description)
        for description in SWITCHES
    )


class DaikinAirBaseHotWaterSwitch(DaikinAirBaseHotWaterEntity, SwitchEntity):
    """Switch for a hot water boolean control."""

    entity_description: AirBaseHotWaterSwitchEntityDescription

    def __init__(
        self,
        coordinator,
        description: AirBaseHotWaterSwitchEntityDescription,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, description.translation_key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return whether the switch is on."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.coordinator.async_set_control(
            **{self.entity_description.control_key: True}
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.coordinator.async_set_control(
            **{self.entity_description.control_key: False}
        )
