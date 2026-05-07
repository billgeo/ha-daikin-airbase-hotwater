"""Tests for setup, coordinator, and config flow behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import custom_components.daikin_airbase_hotwater as integration
from custom_components.daikin_airbase_hotwater import config_flow
from custom_components.daikin_airbase_hotwater.api import (
    AirBaseHotWaterConnectionError,
    AirBaseHotWaterDayPower,
    AirBaseHotWaterError,
    AirBaseHotWaterResponseError,
)
from custom_components.daikin_airbase_hotwater.config_flow import (
    CannotConnect,
    DaikinAirBaseHotWaterConfigFlow,
    InvalidResponse,
)
from custom_components.daikin_airbase_hotwater.const import CONF_PORT, DOMAIN, PLATFORMS
from custom_components.daikin_airbase_hotwater.coordinator import (
    DaikinAirBaseHotWaterCoordinator,
)


def _status() -> SimpleNamespace:
    """Return coordinator status data."""
    return SimpleNamespace(mode="auto")


def _day_power() -> AirBaseHotWaterDayPower:
    """Return zeroed day power."""
    return AirBaseHotWaterDayPower.from_raw(
        {
            "ep_day0_2hours": "0;0;0;0;0;0;0;0;0;0;0;0",
            "ep_day1_2hours": "0;0;0;0;0;0;0;0;0;0;0;0",
        }
    )


class FakeConfigEntries:
    """Config entry manager test double."""

    def __init__(self, unload_ok: bool = True) -> None:
        """Initialise fake manager."""
        self.forwarded = []
        self.unloaded = []
        self.unload_ok = unload_ok

    async def async_forward_entry_setups(
        self,
        entry: Any,
        platforms: list[str],
    ) -> None:
        """Record forwarded platforms."""
        self.forwarded.append((entry, platforms))

    async def async_unload_platforms(self, entry: Any, platforms: list[str]) -> bool:
        """Record unloaded platforms."""
        self.unloaded.append((entry, platforms))
        return self.unload_ok


class FakeHass:
    """Home Assistant test double."""

    def __init__(self, unload_ok: bool = True) -> None:
        """Initialise fake hass."""
        self.data: dict[str, Any] = {}
        self.config_entries = FakeConfigEntries(unload_ok)
        self.session = object()


class FakeApi:
    """API test double."""

    def __init__(
        self,
        status: SimpleNamespace | Exception | None = None,
        day_power: AirBaseHotWaterDayPower | Exception | None = None,
    ) -> None:
        """Initialise fake API."""
        self.status = status or _status()
        self.day_power = day_power or _day_power()
        self.status_calls = 0
        self.day_power_calls = 0
        self.control_calls = []

    async def get_status(self) -> SimpleNamespace:
        """Return or raise status."""
        self.status_calls += 1
        if isinstance(self.status, Exception):
            raise self.status
        return self.status

    async def get_day_power(self) -> AirBaseHotWaterDayPower:
        """Return or raise day power."""
        self.day_power_calls += 1
        if isinstance(self.day_power, Exception):
            raise self.day_power
        return self.day_power

    async def set_control(self, **kwargs: Any) -> None:
        """Record control writes."""
        self.control_calls.append(kwargs)


async def test_setup_and_unload_entry(monkeypatch):
    """Test integration setup and unload paths."""
    coordinator = SimpleNamespace(async_config_entry_first_refresh=lambda: None)

    async def first_refresh() -> None:
        coordinator.refreshed = True

    coordinator.async_config_entry_first_refresh = first_refresh
    monkeypatch.setattr(
        integration,
        "async_get_clientsession",
        lambda hass: hass.session,
    )
    monkeypatch.setattr(
        integration,
        "DaikinAirBaseHotWaterApi",
        lambda host, session, *, port: ("api", host, session, port),
    )
    monkeypatch.setattr(
        integration,
        "DaikinAirBaseHotWaterCoordinator",
        lambda hass, entry, api: coordinator,
    )
    hass = FakeHass()
    entry = SimpleNamespace(
        data={"host": "192.0.2.10", CONF_PORT: 8080},
        entry_id="entry",
    )

    assert await integration.async_setup_entry(hass, entry) is True
    assert coordinator.refreshed is True
    assert entry.runtime_data is coordinator
    assert hass.data[DOMAIN]["entry"] is coordinator
    assert hass.config_entries.forwarded == [(entry, PLATFORMS)]

    assert await integration.async_unload_entry(hass, entry) is True
    assert "entry" not in hass.data[DOMAIN]

    hass = FakeHass(unload_ok=False)
    hass.data[DOMAIN] = {"entry": coordinator}
    assert await integration.async_unload_entry(hass, entry) is False
    assert hass.data[DOMAIN]["entry"] is coordinator


async def test_coordinator_refreshes_status_energy_and_controls():
    """Test coordinator refresh cadence and control refresh."""
    api = FakeApi()
    entry = SimpleNamespace()
    coordinator = DaikinAirBaseHotWaterCoordinator(None, entry, api)

    assert await coordinator._async_update_data() is api.status
    assert coordinator.energy_data is api.day_power
    assert api.day_power_calls == 1

    await coordinator._async_maybe_update_energy_data()
    assert api.day_power_calls == 1

    await coordinator.async_set_control(power=True)
    assert api.control_calls == [{"power": True}]
    assert coordinator.data is api.status


async def test_coordinator_wraps_status_errors_and_keeps_energy_optional():
    """Test coordinator error handling."""
    coordinator = DaikinAirBaseHotWaterCoordinator(
        None,
        SimpleNamespace(),
        FakeApi(status=AirBaseHotWaterError("offline")),
    )

    with pytest.raises(Exception, match="offline"):
        await coordinator._async_update_data()

    coordinator = DaikinAirBaseHotWaterCoordinator(
        None,
        SimpleNamespace(),
        FakeApi(day_power=AirBaseHotWaterError("no energy")),
    )

    assert await coordinator._async_update_data() is coordinator.api.status
    assert coordinator.energy_data is None


async def test_validate_input_maps_api_errors(monkeypatch):
    """Test config-flow input validation error mapping."""

    class ApiFactory:
        def __init__(self, error: Exception | None = None) -> None:
            self.error = error

        async def get_status(self) -> None:
            if self.error is not None:
                raise self.error

    monkeypatch.setattr(
        config_flow,
        "async_get_clientsession",
        lambda hass: hass.session,
    )
    monkeypatch.setattr(
        config_flow,
        "DaikinAirBaseHotWaterApi",
        lambda host, session, *, port: ApiFactory(),
    )
    await config_flow._validate_input(FakeHass(), "192.0.2.10", 80)

    monkeypatch.setattr(
        config_flow,
        "DaikinAirBaseHotWaterApi",
        lambda host, session, *, port: ApiFactory(AirBaseHotWaterConnectionError("no")),
    )
    with pytest.raises(CannotConnect):
        await config_flow._validate_input(FakeHass(), "192.0.2.10", 80)

    monkeypatch.setattr(
        config_flow,
        "DaikinAirBaseHotWaterApi",
        lambda host, session, *, port: ApiFactory(AirBaseHotWaterResponseError("bad")),
    )
    with pytest.raises(InvalidResponse):
        await config_flow._validate_input(FakeHass(), "192.0.2.10", 80)


async def test_config_flow_user_step(monkeypatch):
    """Test config flow form, success, and error paths."""
    flow = DaikinAirBaseHotWaterConfigFlow()
    flow.hass = FakeHass()

    result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["errors"] == {}

    async def validate_success(hass: Any, host: str, port: int) -> None:
        return None

    monkeypatch.setattr(config_flow, "_validate_input", validate_success)
    result = await flow.async_step_user({"host": "192.0.2.10", CONF_PORT: 80})
    assert result == {
        "type": "create_entry",
        "title": "Daikin hot water (192.0.2.10)",
        "data": {"host": "192.0.2.10", CONF_PORT: 80},
    }
    assert flow.unique_id == "192.0.2.10:80"
    assert flow.abort_checked is True

    for error, expected in (
        (CannotConnect, "cannot_connect"),
        (InvalidResponse, "invalid_response"),
        (RuntimeError, "unknown"),
    ):

        async def validate_error(hass: Any, host: str, port: int) -> None:
            raise error

        monkeypatch.setattr(config_flow, "_validate_input", validate_error)
        result = await flow.async_step_user({"host": "192.0.2.10", CONF_PORT: 80})
        assert result["type"] == "form"
        assert result["errors"] == {"base": expected}
