"""Sensor entities for Daikin AirBase Hot Water."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .api import AirBaseHotWaterDayPower, AirBaseHotWaterStatus
from .coordinator import DaikinAirBaseHotWaterConfigEntry
from .entity import DaikinAirBaseHotWaterEntity


@dataclass(frozen=True, kw_only=True)
class AirBaseHotWaterSensorEntityDescription(SensorEntityDescription):
    """Description for a hot water sensor."""

    value_fn: Callable[[AirBaseHotWaterStatus], StateType]


@dataclass(frozen=True, kw_only=True)
class AirBaseHotWaterEnergySensorEntityDescription(SensorEntityDescription):
    """Description for a hot water energy sensor."""

    value_fn: Callable[[AirBaseHotWaterDayPower], StateType]


SENSORS: tuple[AirBaseHotWaterSensorEntityDescription, ...] = (
    AirBaseHotWaterSensorEntityDescription(
        key="tank_temperature",
        translation_key="tank_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.temp_tank,
    ),
    AirBaseHotWaterSensorEntityDescription(
        key="target_temperature",
        translation_key="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.temp_set,
    ),
    AirBaseHotWaterSensorEntityDescription(
        key="outside_temperature",
        translation_key="outside_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.temp_outside,
    ),
)

ENERGY_SENSORS: tuple[AirBaseHotWaterEnergySensorEntityDescription, ...] = (
    AirBaseHotWaterEnergySensorEntityDescription(
        key="energy_today",
        translation_key="energy_period",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda day_power: day_power.current_period_energy(dt_util.now()),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DaikinAirBaseHotWaterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator = entry.runtime_data
    entities = [
        DaikinAirBaseHotWaterSensor(coordinator, description) for description in SENSORS
    ]
    entities.extend(
        DaikinAirBaseHotWaterEnergySensor(coordinator, description)
        for description in ENERGY_SENSORS
    )
    async_add_entities(entities)


class DaikinAirBaseHotWaterSensor(DaikinAirBaseHotWaterEntity, SensorEntity):
    """Sensor for a hot water status value."""

    entity_description: AirBaseHotWaterSensorEntityDescription

    def __init__(
        self,
        coordinator,
        description: AirBaseHotWaterSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.translation_key, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)


class DaikinAirBaseHotWaterEnergySensor(
    DaikinAirBaseHotWaterEntity,
    SensorEntity,
):
    """Sensor for a hot water energy value."""

    entity_description: AirBaseHotWaterEnergySensorEntityDescription

    def __init__(
        self,
        coordinator,
        description: AirBaseHotWaterEnergySensorEntityDescription,
    ) -> None:
        """Initialise the energy sensor."""
        super().__init__(coordinator, description.translation_key, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return whether the energy sensor has data."""
        return super().available and self.coordinator.energy_data is not None

    @property
    def native_value(self) -> StateType:
        """Return the current energy sensor value."""
        if self.coordinator.energy_data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.energy_data)
