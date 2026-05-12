"""Local API client for Daikin AirBase hot water controllers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from math import fsum
import re
from typing import Any
from urllib.parse import unquote

from aiohttp import ClientError, ClientResponseError, ClientSession

GET_UNIT_INFO = "skyfi/hotwater/get_unit_info"
GET_DAY_POWER = "skyfi/hotwater/get_day_power"
SET_CONTROL_INFO = "skyfi/hotwater/set_control_info"
MAX_VACATION_DAYS = 365
DRIVE_TIME_SLOT_MINUTES = 30
DRIVE_TIME_SLOTS_PER_DAY = 24 * 60 // DRIVE_TIME_SLOT_MINUTES
DAY_POWER_2HOUR_BUCKETS = 12
DAY_POWER_PERIOD_MINUTES = 24 * 60 // DAY_POWER_2HOUR_BUCKETS
DAY_POWER_PERIOD_HOURS = DAY_POWER_PERIOD_MINUTES / 60

DRIVE_PROGRAM_LABELS = {
    1: "set_01",
    2: "set_02",
    3: "set_03",
    4: "set_04",
    5: "program_1",
    6: "program_1_and_2",
}

DRIVE_PROGRAM_ALIASES = {
    "set_01": 1,
    "set_1": 1,
    "set01": 1,
    "set1": 1,
    "set_02": 2,
    "set_2": 2,
    "set02": 2,
    "set2": 2,
    "set_03": 3,
    "set_3": 3,
    "set03": 3,
    "set3": 3,
    "set_04": 4,
    "set_4": 4,
    "set04": 4,
    "set4": 4,
    "program_1": 5,
    "program1": 5,
    "prog_1": 5,
    "prog1": 5,
    "drive_p1": 5,
    "program_1_and_2": 6,
    "programs_1_and_2": 6,
    "program_1_2": 6,
    "programs_1_2": 6,
    "prog_1_and_2": 6,
    "progs_1_and_2": 6,
    "prog_1_2": 6,
    "progs_1_2": 6,
    "drive_p1_p2": 6,
    "program_2": 6,
    "program2": 6,
    "prog_2": 6,
    "prog2": 6,
    "drive_p2": 6,
}

BOOL_CONTROL_FIELDS = {"pow", "boost", "vacation"}
INT_CONTROL_FIELDS = {
    "boil_level",
    "vacation_days",
    "drive_p",
    "drive_p1s",
    "drive_p1e",
    "drive_p2s",
    "drive_p2e",
}
READ_ONLY_FIELDS = {"temp_set", "temp_tank", "temp_outside"}
VALID_CONTROL_FIELDS = BOOL_CONTROL_FIELDS | INT_CONTROL_FIELDS
CONTROL_ALIASES = {
    "power": "pow",
    "drive_program": "drive_p",
    "drive_program_selection": "drive_p",
    "program1_start": "drive_p1s",
    "program1_end": "drive_p1e",
    "program2_start": "drive_p2s",
    "program2_end": "drive_p2e",
    "program_1_start": "drive_p1s",
    "program_1_end": "drive_p1e",
    "program_2_start": "drive_p2s",
    "program_2_end": "drive_p2e",
}


class AirBaseHotWaterError(Exception):
    """Base exception for AirBase hot water API failures."""


class AirBaseHotWaterConnectionError(AirBaseHotWaterError):
    """Raised when the controller cannot be reached."""


class AirBaseHotWaterResponseError(AirBaseHotWaterError):
    """Raised when the controller returns an invalid response."""


@dataclass(frozen=True)
class AirBaseHotWaterStatus:
    """Typed status for a Daikin AirBase hot water controller."""

    power: bool | None
    boost: bool | None
    vacation: bool | None
    vacation_days: int | None
    boil_level: int | None
    mode: str | None
    temp_set: float | None
    temp_tank: float | None
    temp_outside: float | None
    drive_p: int | None
    drive_program: str | None
    set_program: int | None
    manual_program_1: bool | None
    manual_program_2: bool | None
    drive_p1s: int | None
    drive_p1e: int | None
    drive_p2s: int | None
    drive_p2e: int | None
    program_1_start: str | None
    program_1_end: str | None
    program_2_start: str | None
    program_2_end: str | None

    @classmethod
    def from_raw(cls, raw: dict[str, str]) -> AirBaseHotWaterStatus:
        """Build typed status from the controller response fields."""
        power = _to_bool(raw.get("pow"), "pow")
        boil_level = _to_int(raw.get("boil_level"), "boil_level")
        drive_program_value = _to_drive_program_value(raw.get("drive_p"))
        mode = _status_mode(power, boil_level)

        return cls(
            power=power,
            boost=_to_bool(raw.get("boost"), "boost"),
            vacation=_to_bool(raw.get("vacation"), "vacation"),
            vacation_days=_to_int(raw.get("vacation_days"), "vacation_days"),
            boil_level=boil_level,
            mode=mode,
            temp_set=_to_float(raw.get("temp_set"), "temp_set"),
            temp_tank=_to_float(raw.get("temp_tank"), "temp_tank"),
            temp_outside=_to_float(raw.get("temp_outside"), "temp_outside"),
            drive_p=drive_program_value,
            drive_program=_drive_program_label(drive_program_value),
            set_program=_drive_set_program(drive_program_value),
            manual_program_1=_manual_program_1_enabled(drive_program_value),
            manual_program_2=_manual_program_2_enabled(drive_program_value),
            drive_p1s=_to_drive_time_slot(raw.get("drive_p1s"), "drive_p1s"),
            drive_p1e=_to_drive_time_slot(raw.get("drive_p1e"), "drive_p1e"),
            drive_p2s=_to_drive_time_slot(raw.get("drive_p2s"), "drive_p2s"),
            drive_p2e=_to_drive_time_slot(raw.get("drive_p2e"), "drive_p2e"),
            program_1_start=_to_drive_time(raw.get("drive_p1s"), "drive_p1s"),
            program_1_end=_to_drive_time(raw.get("drive_p1e"), "drive_p1e"),
            program_2_start=_to_drive_time(raw.get("drive_p2s"), "drive_p2s"),
            program_2_end=_to_drive_time(raw.get("drive_p2e"), "drive_p2e"),
        )


@dataclass(frozen=True)
class AirBaseHotWaterEnergyPeriod:
    """Energy used during one API reporting period."""

    energy_kwh: float
    start: datetime
    end: datetime

    @property
    def average_power_watts(self) -> float:
        """Return average power for the period."""
        return self.energy_kwh * 1000 / DAY_POWER_PERIOD_HOURS


@dataclass(frozen=True)
class AirBaseHotWaterDayPower:
    """Typed current and previous day energy summaries."""

    current_day_2hours: tuple[float, ...]
    previous_day_2hours: tuple[float, ...]
    current_day_total: float
    previous_day_total: float

    def current_period_energy(self, at: datetime) -> float:
        """Return current-day energy for the API period containing the time."""
        period = (at.hour * 60 + at.minute) // DAY_POWER_PERIOD_MINUTES
        return self.current_day_2hours[period]

    def previous_completed_period(self, at: datetime) -> AirBaseHotWaterEnergyPeriod:
        """Return the last completed API reporting period."""
        day_start = at.replace(hour=0, minute=0, second=0, microsecond=0)
        current_period = (at.hour * 60 + at.minute) // DAY_POWER_PERIOD_MINUTES

        if current_period == 0:
            period_end = day_start
            return AirBaseHotWaterEnergyPeriod(
                energy_kwh=self.previous_day_2hours[-1],
                start=period_end - timedelta(minutes=DAY_POWER_PERIOD_MINUTES),
                end=period_end,
            )

        period_start = day_start + timedelta(
            minutes=(current_period - 1) * DAY_POWER_PERIOD_MINUTES
        )
        return AirBaseHotWaterEnergyPeriod(
            energy_kwh=self.current_day_2hours[current_period - 1],
            start=period_start,
            end=period_start + timedelta(minutes=DAY_POWER_PERIOD_MINUTES),
        )

    def previous_period_average_power_watts(self, at: datetime) -> float:
        """Return average watts for the last completed API reporting period."""
        return self.previous_completed_period(at).average_power_watts

    @classmethod
    def from_raw(cls, raw: dict[str, str]) -> AirBaseHotWaterDayPower:
        """Build typed day power values from the controller response fields."""
        current_day_2hours = _to_float_series(
            raw.get("ep_day0_2hours"),
            "ep_day0_2hours",
            expected_length=DAY_POWER_2HOUR_BUCKETS,
        )
        previous_day_2hours = _to_float_series(
            raw.get("ep_day1_2hours"),
            "ep_day1_2hours",
            expected_length=DAY_POWER_2HOUR_BUCKETS,
        )
        return cls(
            current_day_2hours=current_day_2hours,
            previous_day_2hours=previous_day_2hours,
            current_day_total=fsum(current_day_2hours),
            previous_day_total=fsum(previous_day_2hours),
        )


class DaikinAirBaseHotWaterApi:
    """Async client for the local AirBase hot water API."""

    def __init__(
        self,
        host: str,
        session: ClientSession,
        *,
        port: int = 80,
        request_timeout: int = 10,
    ) -> None:
        """Initialise the API client."""
        self.host = host
        self.port = port
        self._session = session
        self._request_timeout = request_timeout
        if port == 80:
            self.base_url = f"http://{host}"
        else:
            self.base_url = f"http://{host}:{port}"

    async def get_status(self) -> AirBaseHotWaterStatus:
        """Fetch typed hot water status."""
        raw = await self._get(GET_UNIT_INFO)
        return AirBaseHotWaterStatus.from_raw(raw)

    async def get_day_power(self) -> AirBaseHotWaterDayPower:
        """Fetch current and previous day energy summaries."""
        raw = await self._get(GET_DAY_POWER)
        return AirBaseHotWaterDayPower.from_raw(raw)

    async def set_control(self, **kwargs: Any) -> None:
        """Set writable hot water controls."""
        params = normalize_control_params(kwargs)
        if not params:
            return
        await self._get(SET_CONTROL_INFO, params=params)

    async def set_power(self, value: bool | str | int) -> None:
        """Turn the hot water system on or off."""
        await self.set_control(power=value)

    async def set_boost(self, value: bool | str | int) -> None:
        """Turn boost mode on or off."""
        await self.set_control(boost=value)

    async def set_vacation(self, value: bool | str | int) -> None:
        """Turn vacation mode on or off."""
        await self.set_control(vacation=value)

    async def set_vacation_days(self, days: int) -> None:
        """Set vacation days."""
        await self.set_control(vacation_days=days)

    async def set_boil_level(self, level: int) -> None:
        """Set boil level, where 0 is auto and 1-6 are manual levels."""
        await self.set_control(boil_level=level)

    async def set_mode_auto(self) -> None:
        """Power on and set automatic boil mode."""
        await self.set_control(mode="auto")

    async def set_mode_manual(self, level: int) -> None:
        """Power on and set manual boil mode."""
        await self.set_control(mode="manual", boil_level=level)

    async def set_drive_program_selection(self, program: Any) -> None:
        """Set active drive program."""
        await self.set_control(drive_program=program)

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Make a GET request and parse the controller response."""
        url = f"{self.base_url}/{path}"
        try:
            async with self._session.get(
                url,
                params=params,
                timeout=self._request_timeout,
            ) as response:
                response.raise_for_status()
                return parse_response(await response.text())
        except ClientResponseError as exc:
            raise AirBaseHotWaterConnectionError(str(exc)) from exc
        except ClientError as exc:
            raise AirBaseHotWaterConnectionError(str(exc)) from exc


def parse_response(response_body: str) -> dict[str, str]:
    """Parse comma-separated key=value AirBase hot water responses."""
    response = dict(
        (match.group(1), match.group(2))
        for match in re.finditer(r"(\w+)=([^=]*)(?:,|$)", response_body)
    )
    if "ret" not in response:
        raise AirBaseHotWaterResponseError("missing 'ret' field in response")
    ret = response.pop("ret")
    if ret != "OK":
        raise AirBaseHotWaterResponseError(f"ret={ret!r}")
    return response


def normalize_control_params(params: dict[str, Any]) -> dict[str, str]:
    """Validate and convert control parameters for the device API."""
    normalized: dict[str, str] = {}
    aliased_params = {
        CONTROL_ALIASES.get(key, key): value for key, value in params.items()
    }

    mode = aliased_params.pop("mode", None)
    if mode is not None:
        _normalize_mode(mode, aliased_params, normalized)

    for key, value in aliased_params.items():
        if key in READ_ONLY_FIELDS:
            raise ValueError(f"{key} is read-only and cannot be set")
        if key not in VALID_CONTROL_FIELDS:
            raise ValueError(f"Unsupported control parameter: {key}")

        if key in BOOL_CONTROL_FIELDS:
            normalized[key] = _normalize_bool_control(key, value)
        elif key == "boil_level":
            normalized[key] = str(_validate_int_range(key, value, minimum=0, maximum=6))
        elif key == "vacation_days":
            normalized[key] = str(
                _validate_int_range(
                    key,
                    value,
                    minimum=0,
                    maximum=MAX_VACATION_DAYS,
                )
            )
        elif key == "drive_p":
            normalized[key] = str(_normalize_drive_program(value))
        elif key in {"drive_p1s", "drive_p1e", "drive_p2s", "drive_p2e"}:
            normalized[key] = str(_normalize_drive_time(key, value))

    return normalized


def _normalize_mode(
    mode: Any,
    params: dict[str, Any],
    normalized: dict[str, str],
) -> None:
    """Normalize operation mode into writable controls."""
    if mode == "off":
        normalized["pow"] = "0"
    elif mode == "auto":
        if "boil_level" in params:
            boil_level = _validate_int_range(
                "boil_level", params["boil_level"], minimum=0, maximum=6
            )
            if boil_level != 0:
                raise ValueError("auto mode requires boil_level 0")
            params.pop("boil_level")
        normalized["pow"] = "1"
        normalized["boil_level"] = "0"
    elif mode == "manual":
        if "boil_level" not in params:
            raise ValueError("manual mode requires boil_level")
        normalized["pow"] = "1"
    else:
        raise ValueError(f"Unsupported mode for AirBase hot water: {mode}")


def _normalize_bool_control(key: str, value: Any) -> str:
    """Normalize a bool-like control value to 0 or 1."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int) and value in (0, 1):
        return str(value)
    if isinstance(value, str):
        if value in {"0", "1"}:
            return value
        if value in {"off", "on"}:
            return "1" if value == "on" else "0"
    raise ValueError(f"{key} must be a boolean or 0/1")


def _validate_int_range(key: str, value: Any, *, minimum: int, maximum: int) -> int:
    """Validate an integer falls inside an inclusive range."""
    if isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    try:
        int_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc
    if int_value < minimum or int_value > maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    return int_value


def _normalize_drive_time(key: str, value: Any) -> int:
    """Normalize a drive program time to a half-hour slot."""
    if isinstance(value, time):
        return _time_parts_to_drive_slot(key, value.hour, value.minute)
    if isinstance(value, str):
        if re.fullmatch(r"\d+", value):
            return _validate_drive_time_slot(key, value)
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
        if match:
            return _time_parts_to_drive_slot(
                key,
                int(match.group(1)),
                int(match.group(2)),
            )
        raise ValueError(f"{key} must be a 0-47 slot or HH:MM time")
    return _validate_drive_time_slot(key, value)


def _validate_drive_time_slot(key: str, value: Any) -> int:
    """Validate a drive program time slot."""
    return _validate_int_range(
        key, value, minimum=0, maximum=DRIVE_TIME_SLOTS_PER_DAY - 1
    )


def _normalize_drive_program(value: Any) -> int:
    """Normalize a drive program selector to its API value."""
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in DRIVE_PROGRAM_ALIASES:
            return DRIVE_PROGRAM_ALIASES[normalized]
    return _validate_int_range("drive_p", value, minimum=1, maximum=6)


def _time_parts_to_drive_slot(key: str, hour: int, minute: int) -> int:
    """Convert HH:MM parts to a half-hour drive time slot."""
    if hour < 0 or hour > 23:
        raise ValueError(f"{key} hour must be between 0 and 23")
    if minute % DRIVE_TIME_SLOT_MINUTES != 0 or minute < 0 or minute > 59:
        raise ValueError(f"{key} must use 30 minute increments")
    return (hour * 60 + minute) // DRIVE_TIME_SLOT_MINUTES


def _drive_time_slot_to_time(value: Any, key: str) -> str:
    """Convert a half-hour drive time slot to HH:MM."""
    slot = _validate_drive_time_slot(key, value)
    minutes = slot * DRIVE_TIME_SLOT_MINUTES
    hour, minute = divmod(minutes, 60)
    return f"{hour:02d}:{minute:02d}"


def _to_bool(value: str | None, key: str) -> bool | None:
    """Convert a 0/1 status value to bool."""
    if _is_missing(value):
        return None
    if value == "1":
        return True
    if value == "0":
        return False
    raise AirBaseHotWaterResponseError(f"{key} must be 0 or 1, got {value!r}")


def _to_int(value: str | None, key: str) -> int | None:
    """Convert a status value to int."""
    if _is_missing(value):
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise AirBaseHotWaterResponseError(
            f"{key} must be an integer, got {value!r}"
        ) from exc


def _to_float(value: str | None, key: str) -> float | None:
    """Convert a status value to float."""
    if _is_missing(value):
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise AirBaseHotWaterResponseError(
            f"{key} must be a float, got {value!r}"
        ) from exc


def _to_float_series(
    value: str | None,
    key: str,
    *,
    expected_length: int,
) -> tuple[float, ...]:
    """Convert a semicolon-separated numeric response value to floats."""
    if _is_missing(value):
        raise AirBaseHotWaterResponseError(f"missing {key!r} field in response")

    decoded_value = unquote(value)
    parts = decoded_value.split(";")
    if len(parts) != expected_length:
        raise AirBaseHotWaterResponseError(
            f"{key} must contain {expected_length} values, got {len(parts)}"
        )

    try:
        return tuple(float(part) for part in parts)
    except ValueError as exc:
        raise AirBaseHotWaterResponseError(
            f"{key} must contain float values, got {decoded_value!r}"
        ) from exc


def _to_drive_time_slot(value: str | None, key: str) -> int | None:
    """Convert a status drive program time to its raw half-hour slot."""
    if _is_missing(value):
        return None
    try:
        return _validate_drive_time_slot(key, value)
    except ValueError as exc:
        raise AirBaseHotWaterResponseError(str(exc)) from exc


def _to_drive_time(value: str | None, key: str) -> str | None:
    """Convert a status drive program time to HH:MM."""
    if _is_missing(value):
        return None
    try:
        return _drive_time_slot_to_time(value, key)
    except ValueError as exc:
        raise AirBaseHotWaterResponseError(str(exc)) from exc


def _to_drive_program_value(value: str | None) -> int | None:
    """Convert a status drive program selector to its raw value."""
    if _is_missing(value):
        return None
    try:
        return _normalize_drive_program(value)
    except ValueError as exc:
        raise AirBaseHotWaterResponseError(str(exc)) from exc


def _drive_program_label(raw_value: int | None) -> str | None:
    """Return the generic label for a drive program selector."""
    if raw_value is None:
        return None
    return DRIVE_PROGRAM_LABELS.get(raw_value)


def _drive_set_program(raw_value: int | None) -> int | None:
    """Return selected fixed set program number, if any."""
    if raw_value is None or raw_value > 4:
        return None
    return raw_value


def _manual_program_1_enabled(raw_value: int | None) -> bool | None:
    """Return whether manual program 1 is selected."""
    if raw_value is None:
        return None
    return raw_value in {5, 6}


def _manual_program_2_enabled(raw_value: int | None) -> bool | None:
    """Return whether manual program 2 is selected."""
    if raw_value is None:
        return None
    return raw_value == 6


def _status_mode(power: bool | None, boil_level: int | None) -> str | None:
    """Derive a Home Assistant-friendly operation mode."""
    if power is False:
        return "off"
    if boil_level is None:
        return None
    return "auto" if boil_level == 0 else "manual"


def _is_missing(value: str | None) -> bool:
    """Return True when a status field is absent or intentionally blank."""
    return value in (None, "", "-")
