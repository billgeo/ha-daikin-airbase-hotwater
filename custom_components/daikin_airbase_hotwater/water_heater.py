"""Water heater entity for Daikin AirBase Hot Water."""

from __future__ import annotations

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MODE_AUTO, MODE_MANUAL, MODE_OFF
from .coordinator import DaikinAirBaseHotWaterConfigEntry
from .entity import DaikinAirBaseHotWaterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DaikinAirBaseHotWaterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up water heater entities."""
    async_add_entities([DaikinAirBaseHotWaterWaterHeater(entry.runtime_data)])


class DaikinAirBaseHotWaterWaterHeater(
    DaikinAirBaseHotWaterEntity,
    WaterHeaterEntity,
):
    """Representation of the hot water controller as a water heater."""

    _attr_name = None
    _attr_operation_list = [MODE_OFF, MODE_AUTO, MODE_MANUAL]
    _attr_supported_features = WaterHeaterEntityFeature.OPERATION_MODE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator) -> None:
        """Initialise the water heater."""
        super().__init__(coordinator, "water_heater")

    @property
    def current_operation(self) -> str | None:
        """Return current operation mode."""
        return self.coordinator.data.mode

    @property
    def current_temperature(self) -> float | None:
        """Return current tank temperature."""
        return self.coordinator.data.temp_tank

    @property
    def target_temperature(self) -> float | None:
        """Return read-only target temperature reported by the controller."""
        return self.coordinator.data.temp_set

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set operation mode."""
        if operation_mode == MODE_OFF:
            await self.coordinator.async_set_control(mode=MODE_OFF)
            return
        if operation_mode == MODE_AUTO:
            await self.coordinator.async_set_control(mode=MODE_AUTO)
            return
        if operation_mode == MODE_MANUAL:
            level = self.coordinator.data.boil_level
            if level is None or level == 0:
                level = 1
            await self.coordinator.async_set_control(mode=MODE_MANUAL, boil_level=level)
            return
        raise ValueError(f"Unsupported operation mode: {operation_mode}")

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the hot water controller on."""
        if self.coordinator.data.boil_level == 0:
            await self.coordinator.async_set_control(mode=MODE_AUTO)
        else:
            await self.coordinator.async_set_control(power=True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the hot water controller off."""
        await self.coordinator.async_set_control(power=False)
