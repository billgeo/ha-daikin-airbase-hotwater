"""Tests for the vendored AirBase hot water API client."""

from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import sys
from typing import Any

import pytest

API_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "daikin_airbase_hotwater"
    / "api.py"
)
SPEC = importlib.util.spec_from_file_location("airbase_hotwater_api", API_PATH)
assert SPEC is not None
assert SPEC.loader is not None
api_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = api_module
SPEC.loader.exec_module(api_module)

AirBaseHotWaterResponseError = api_module.AirBaseHotWaterResponseError
AirBaseHotWaterDayPower = api_module.AirBaseHotWaterDayPower
DaikinAirBaseHotWaterApi = api_module.DaikinAirBaseHotWaterApi
normalize_control_params = api_module.normalize_control_params
parse_response = api_module.parse_response


class FakeResponse:
    """Minimal aiohttp response test double."""

    def __init__(self, body: str) -> None:
        """Initialise the fake response."""
        self._body = body

    async def __aenter__(self) -> FakeResponse:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the async context manager."""

    def raise_for_status(self) -> None:
        """Match aiohttp's response API."""

    async def text(self) -> str:
        """Return response body text."""
        return self._body


class FakeSession:
    """Minimal aiohttp session test double."""

    def __init__(self, *responses: str) -> None:
        """Initialise the fake session."""
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> FakeResponse:
        """Record a GET request and return the next fake response."""
        self.requests.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(self._responses.pop(0))


@pytest.mark.asyncio
async def test_get_status_returns_typed_values():
    """Test fetching typed hot water status."""
    session = FakeSession(
        "ret=OK,pow=1,boost=0,vacation=0,vacation_days=3,"
        "temp_set=63.0,temp_tank=56,temp_outside=13,boil_level=0,drive_p=5,"
        "drive_p1s=42,drive_p1e=14,drive_p2s=22,drive_p2e=28"
    )

    api = DaikinAirBaseHotWaterApi("ip", session)
    status = await api.get_status()

    assert status.power is True
    assert status.boost is False
    assert status.vacation is False
    assert status.vacation_days == 3
    assert status.boil_level == 0
    assert status.mode == "auto"
    assert status.temp_set == 63.0
    assert status.temp_tank == 56.0
    assert status.temp_outside == 13.0
    assert status.drive_p == 5
    assert status.drive_program == "program_1"
    assert status.set_program is None
    assert status.manual_program_1 is True
    assert status.manual_program_2 is False
    assert status.program_1_start == "21:00"
    assert status.program_1_end == "07:00"
    assert status.program_2_start == "11:00"
    assert status.program_2_end == "14:00"
    assert session.requests == [
        {
            "url": "http://ip/skyfi/hotwater/get_unit_info",
            "params": None,
            "timeout": 10,
        }
    ]


@pytest.mark.asyncio
async def test_get_status_reports_off_mode():
    """Test power off is represented as the off operation mode."""
    session = FakeSession("ret=OK,pow=0,boil_level=4")

    api = DaikinAirBaseHotWaterApi("ip", session)
    status = await api.get_status()

    assert status.power is False
    assert status.mode == "off"


@pytest.mark.asyncio
async def test_get_day_power_returns_typed_values():
    """Test fetching current and previous day energy summaries."""
    session = FakeSession(
        "ret=OK,"
        "ep_day0_2hours=0.0%3b0.1%3b0.0%3b0.0%3b0.0%3b0.0"
        "%3b0%3b0%3b0%3b0%3b0%3b0,"
        "ep_day1_2hours=0.0%3b0.1%3b0.0%3b0.0%3b0.0%3b0.0"
        "%3b0.0%3b0.0%3b0.0%3b1.4%3b0.3%3b0.0"
    )

    api = DaikinAirBaseHotWaterApi("ip", session)
    day_power = await api.get_day_power()

    assert day_power.current_day_2hours == (
        0.0,
        0.1,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    )
    assert day_power.previous_day_2hours == (
        0.0,
        0.1,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.4,
        0.3,
        0.0,
    )
    assert day_power.current_day_total == pytest.approx(0.1)
    assert day_power.previous_day_total == pytest.approx(1.8)
    assert session.requests == [
        {
            "url": "http://ip/skyfi/hotwater/get_day_power",
            "params": None,
            "timeout": 10,
        }
    ]


def test_day_power_validation():
    """Test day power response validation."""
    valid_previous_day = "0;0;0;0;0;0;0;0;0;0;0;0"

    with pytest.raises(AirBaseHotWaterResponseError):
        AirBaseHotWaterDayPower.from_raw(
            {
                "ep_day0_2hours": "0;0",
                "ep_day1_2hours": valid_previous_day,
            }
        )

    with pytest.raises(AirBaseHotWaterResponseError):
        AirBaseHotWaterDayPower.from_raw(
            {
                "ep_day0_2hours": "0;bad;0;0;0;0;0;0;0;0;0;0",
                "ep_day1_2hours": valid_previous_day,
            }
        )

    with pytest.raises(AirBaseHotWaterResponseError):
        AirBaseHotWaterDayPower.from_raw({"ep_day1_2hours": valid_previous_day})


def test_day_power_current_period_energy():
    """Test current-period energy is read from the matching 2-hour bucket."""
    day_power = AirBaseHotWaterDayPower.from_raw(
        {
            "ep_day0_2hours": "0;1;2;3;4;5;6;7;8;9;10;11",
            "ep_day1_2hours": "0;0;0;0;0;0;0;0;0;0;0;0",
        }
    )

    assert day_power.current_period_energy(datetime(2026, 5, 7, 0, 0)) == 0
    assert day_power.current_period_energy(datetime(2026, 5, 7, 3, 59)) == 1
    assert day_power.current_period_energy(datetime(2026, 5, 7, 23, 59)) == 11


def test_day_power_previous_completed_period():
    """Test previous completed reporting period selection and power conversion."""
    day_power = AirBaseHotWaterDayPower.from_raw(
        {
            "ep_day0_2hours": "0;1;2;3;4;5;6;7;8;9;10;11",
            "ep_day1_2hours": "12;13;14;15;16;17;18;19;20;21;22;23",
        }
    )

    period = day_power.previous_completed_period(datetime(2026, 5, 7, 0, 1))
    assert period.energy_kwh == 23
    assert period.start == datetime(2026, 5, 6, 22, 0)
    assert period.end == datetime(2026, 5, 7, 0, 0)
    assert period.average_power_watts == pytest.approx(11500)

    period = day_power.previous_completed_period(datetime(2026, 5, 7, 5, 59))
    assert period.energy_kwh == 1
    assert period.start == datetime(2026, 5, 7, 2, 0)
    assert period.end == datetime(2026, 5, 7, 4, 0)
    assert day_power.previous_period_average_power_watts(
        datetime(2026, 5, 7, 5, 59)
    ) == pytest.approx(500)


@pytest.mark.asyncio
async def test_set_control_sends_normalized_params():
    """Test setting multiple writable controls."""
    session = FakeSession("ret=OK")

    api = DaikinAirBaseHotWaterApi("ip", session)
    await api.set_control(
        boil_level=6,
        boost=True,
        vacation=0,
        drive_program="program_1",
        program_1_start="21:00",
        program_1_end="07:00",
    )

    assert session.requests == [
        {
            "url": "http://ip/skyfi/hotwater/set_control_info",
            "params": {
                "boil_level": "6",
                "boost": "1",
                "vacation": "0",
                "drive_p": "5",
                "drive_p1s": "42",
                "drive_p1e": "14",
            },
            "timeout": 10,
        }
    ]


@pytest.mark.asyncio
async def test_mode_helpers():
    """Test mode helper requests."""
    session = FakeSession("ret=OK", "ret=OK", "ret=OK")

    api = DaikinAirBaseHotWaterApi("ip", session)
    await api.set_mode_auto()
    await api.set_mode_manual(3)
    await api.set_power(False)

    assert [request["params"] for request in session.requests] == [
        {"pow": "1", "boil_level": "0"},
        {"pow": "1", "boil_level": "3"},
        {"pow": "0"},
    ]


def test_parse_response_rejects_bad_responses():
    """Test response validation."""
    with pytest.raises(AirBaseHotWaterResponseError):
        parse_response("pow=1")

    with pytest.raises(AirBaseHotWaterResponseError):
        parse_response("ret=NG")


def test_control_validation():
    """Test invalid control values are rejected locally."""
    with pytest.raises(ValueError):
        normalize_control_params({"temp_set": 60})

    with pytest.raises(ValueError):
        normalize_control_params({"boil_level": 7})

    with pytest.raises(ValueError):
        normalize_control_params({"mode": "manual"})

    with pytest.raises(ValueError):
        normalize_control_params({"mode": "auto", "boil_level": 3})

    with pytest.raises(ValueError):
        normalize_control_params({"vacation_days": 366})

    with pytest.raises(ValueError):
        normalize_control_params({"pow": 2})

    with pytest.raises(ValueError):
        normalize_control_params({"drive_program": "set_07"})

    with pytest.raises(ValueError):
        normalize_control_params({"program_1_start": "21:15"})

    assert normalize_control_params(
        {
            "power": "on",
            "boost": "off",
            "vacation_days": 14,
            "drive_program": "set_04",
            "program_1_start": "21:00",
            "program_1_end": "7:00",
            "program_2_start": "22",
            "program_2_end": 28,
        }
    ) == {
        "pow": "1",
        "boost": "0",
        "vacation_days": "14",
        "drive_p": "4",
        "drive_p1s": "42",
        "drive_p1e": "14",
        "drive_p2s": "22",
        "drive_p2e": "28",
    }
