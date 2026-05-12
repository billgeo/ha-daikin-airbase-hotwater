"""Tests for Home Assistant entity behavior."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.daikin_airbase_hotwater import entity as base_entity
from custom_components.daikin_airbase_hotwater import (
    number,
    select,
    sensor,
    switch,
    water_heater,
)
from custom_components.daikin_airbase_hotwater.api import AirBaseHotWaterDayPower
from custom_components.daikin_airbase_hotwater.const import CONF_PORT, DOMAIN


def _status(**overrides: Any) -> SimpleNamespace:
    """Return status data with common defaults."""
    defaults = {
        "boost": True,
        "vacation": False,
        "vacation_days": 3,
        "boil_level": 4,
        "mode": "manual",
        "temp_set": 60.0,
        "temp_tank": 52.5,
        "temp_outside": 12.0,
        "drive_program": "program_1",
        "program_1_start": "21:00",
        "program_1_end": "07:00",
        "program_2_start": "11:00",
        "program_2_end": "14:00",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class FakeCoordinator:
    """Coordinator test double."""

    def __init__(
        self,
        data: SimpleNamespace | None = None,
        energy_data: AirBaseHotWaterDayPower | None = None,
    ) -> None:
        """Initialise the fake coordinator."""
        self.config_entry = SimpleNamespace(
            unique_id="device",
            data={"host": "192.0.2.10", CONF_PORT: 8080},
        )
        self.data = data or _status()
        self.energy_data = energy_data
        self.control_calls: list[dict[str, Any]] = []

    async def async_set_control(self, **kwargs: Any) -> None:
        """Record control writes."""
        self.control_calls.append(kwargs)


def _day_power() -> AirBaseHotWaterDayPower:
    """Return day power with easy-to-read 2-hour bucket values."""
    return AirBaseHotWaterDayPower.from_raw(
        {
            "ep_day0_2hours": "0;1;2;3;4;5;6;7;8;9;10;11",
            "ep_day1_2hours": "0;0;0;0;0;0;0;0;0;0;0;0",
        }
    )


async def test_sensor_entities_report_status_and_period_energy(monkeypatch):
    """Test sensor setup and current values."""
    monkeypatch.setattr(
        sensor.dt_util,
        "now",
        lambda: datetime(2026, 5, 7, 5, 0),
    )
    coordinator = FakeCoordinator(energy_data=_day_power())
    entry = SimpleNamespace(runtime_data=coordinator)
    entities = []

    await sensor.async_setup_entry(None, entry, entities.extend)

    assert [entity._attr_translation_key for entity in entities] == [
        "tank_temperature",
        "target_temperature",
        "outside_temperature",
        "energy_period",
        "average_power",
    ]
    assert [entity.native_value for entity in entities] == [
        52.5,
        60.0,
        12.0,
        2.0,
        500.0,
    ]
    assert entities[-1].extra_state_attributes == {
        "source_period_start": "2026-05-07T02:00:00",
        "source_period_end": "2026-05-07T04:00:00",
        "source_period_hours": 2,
        "source_energy_kwh": 1.0,
    }
    assert entities[-2].extra_state_attributes is None
    assert entities[-1].available is True

    coordinator.energy_data = None
    assert entities[-2].available is False
    assert entities[-2].native_value is None
    assert entities[-1].available is False
    assert entities[-1].native_value is None
    assert entities[-1].extra_state_attributes is None


async def test_average_power_uses_previous_day_at_midnight(monkeypatch):
    """Test average power uses yesterday's final bucket after midnight."""
    monkeypatch.setattr(
        sensor.dt_util,
        "now",
        lambda: datetime(2026, 5, 7, 0, 30),
    )
    day_power = AirBaseHotWaterDayPower.from_raw(
        {
            "ep_day0_2hours": "0;1;2;3;4;5;6;7;8;9;10;11",
            "ep_day1_2hours": "12;13;14;15;16;17;18;19;20;21;22;23",
        }
    )
    coordinator = FakeCoordinator(energy_data=day_power)
    power_sensor = sensor.DaikinAirBaseHotWaterEnergySensor(
        coordinator,
        sensor.ENERGY_SENSORS[1],
    )

    assert power_sensor.native_value == 11500.0
    assert power_sensor.extra_state_attributes == {
        "source_period_start": "2026-05-06T22:00:00",
        "source_period_end": "2026-05-07T00:00:00",
        "source_period_hours": 2,
        "source_energy_kwh": 23.0,
    }


async def test_switch_number_and_select_entities_write_controls():
    """Test control entities expose values and write normalized control keys."""
    coordinator = FakeCoordinator()
    entry = SimpleNamespace(runtime_data=coordinator)
    switches = []
    numbers = []
    selects = []

    await switch.async_setup_entry(None, entry, lambda items: switches.extend(items))
    await number.async_setup_entry(None, entry, lambda items: numbers.extend(items))
    await select.async_setup_entry(None, entry, selects.extend)

    assert [entity.is_on for entity in switches] == [True, False]
    await switches[0].async_turn_off()
    await switches[1].async_turn_on()

    assert [entity.native_value for entity in numbers] == [4, 3]
    await numbers[0].async_set_native_value(6)
    await numbers[1].async_set_native_value(14)

    assert selects[0].options == [
        "Fixed 1: Continuous (24 hours)",
        "Fixed 2: Overnight, 10:00 PM to 7:00 AM (9 hours)",
        "Fixed 3: Early morning, 12:00 AM to 6:00 AM (6 hours)",
        "Fixed 4: Daytime, 10:00 AM to 4:00 PM (6 hours)",
        "Custom 1: 9:00 PM to 7:00 AM (10 hours)",
        "Custom 1 + 2 : 9:00 PM to 7:00 AM and 11:00 AM to 2:00 PM (13 hours total)",
    ]
    assert selects[0].current_option == "Custom 1: 9:00 PM to 7:00 AM (10 hours)"
    await selects[0].async_select_option(selects[0].options[5])

    assert coordinator.control_calls == [
        {"boost": False},
        {"vacation": True},
        {"boil_level": 6},
        {"vacation_days": 14},
        {"drive_program": "program_1_and_2"},
    ]


async def test_select_accepts_existing_internal_drive_program_values():
    """Test existing internal drive program values still work."""
    coordinator = FakeCoordinator()
    entry = SimpleNamespace(runtime_data=coordinator)
    selects = []

    await select.async_setup_entry(None, entry, selects.extend)
    await selects[0].async_select_option("set_04")

    assert coordinator.control_calls == [{"drive_program": "set_04"}]


async def test_water_heater_reports_values_and_writes_modes():
    """Test water heater properties and mode writes."""
    coordinator = FakeCoordinator()
    entry = SimpleNamespace(runtime_data=coordinator)
    entities = []

    await water_heater.async_setup_entry(None, entry, entities.extend)
    heater = entities[0]

    assert heater.current_operation == "manual"
    assert heater.current_temperature == 52.5
    assert heater.target_temperature == 60.0

    await heater.async_set_operation_mode("off")
    await heater.async_set_operation_mode("auto")
    await heater.async_set_operation_mode("manual")
    coordinator.data.boil_level = 0
    await heater.async_set_operation_mode("manual")
    await heater.async_turn_on()
    coordinator.data.boil_level = 2
    await heater.async_turn_on()
    await heater.async_turn_off()

    with pytest.raises(ValueError):
        await heater.async_set_operation_mode("unsupported")

    assert coordinator.control_calls == [
        {"mode": "off"},
        {"mode": "auto"},
        {"mode": "manual", "boil_level": 4},
        {"mode": "manual", "boil_level": 1},
        {"mode": "auto"},
        {"power": True},
        {"power": False},
    ]


def test_base_entity_unique_id_and_device_info():
    """Test base entity metadata."""
    coordinator = FakeCoordinator()

    entity = base_entity.DaikinAirBaseHotWaterEntity(
        coordinator,
        "visible_key",
        "unique_key",
    )

    assert entity._attr_translation_key == "visible_key"
    assert entity._attr_unique_id == "device_unique_key"
    assert entity.device_info["identifiers"] == {(DOMAIN, "device")}
    assert entity.device_info["configuration_url"] == "http://192.0.2.10:8080"

    coordinator.config_entry.data.pop(CONF_PORT)
    assert entity.device_info["configuration_url"] == "http://192.0.2.10"
