"""User-facing labels for AirBase hot water drive programs."""

from __future__ import annotations

from typing import Any

from .api import DRIVE_PROGRAM_LABELS

FIXED_DRIVE_PROGRAM_LABELS = {
    "set_01": "Fixed 1: Continuous (24 hours)",
    "set_02": "Fixed 2: Overnight, 10:00 PM to 7:00 AM (9 hours)",
    "set_03": "Fixed 3: Early morning, 12:00 AM to 6:00 AM (6 hours)",
    "set_04": "Fixed 4: Daytime, 10:00 AM to 4:00 PM (6 hours)",
}


def drive_program_options(status: Any) -> list[str]:
    """Return user-facing drive program options for the current status."""
    return [
        drive_program_label(program, status)
        for program in DRIVE_PROGRAM_LABELS.values()
    ]


def drive_program_label(program: str, status: Any) -> str:
    """Return the user-facing label for a drive program."""
    if program in FIXED_DRIVE_PROGRAM_LABELS:
        return FIXED_DRIVE_PROGRAM_LABELS[program]
    if program == "program_1":
        return _custom_program_label(
            "Custom 1",
            getattr(status, "program_1_start", None),
            getattr(status, "program_1_end", None),
        )
    if program == "program_1_and_2":
        return _combined_custom_program_label(status)
    return program


def drive_program_value(option: str, status: Any) -> str:
    """Return the internal drive program value for a user-facing option."""
    if option in DRIVE_PROGRAM_LABELS.values():
        return option

    labels = {
        drive_program_label(program, status): program
        for program in DRIVE_PROGRAM_LABELS.values()
    }
    return labels.get(option, option)


def _custom_program_label(name: str, start: str | None, end: str | None) -> str:
    window = _format_window(start, end)
    if window is None:
        return name

    range_text, duration_text, _duration_minutes = window
    return f"{name}: {range_text} ({duration_text})"


def _combined_custom_program_label(status: Any) -> str:
    window_1 = _format_window(
        getattr(status, "program_1_start", None),
        getattr(status, "program_1_end", None),
    )
    window_2 = _format_window(
        getattr(status, "program_2_start", None),
        getattr(status, "program_2_end", None),
    )

    range_1 = window_1[0] if window_1 else "Custom 1"
    range_2 = window_2[0] if window_2 else "Custom 2"
    total = ""
    if window_1 and window_2:
        total_minutes = window_1[2] + window_2[2]
        total = f" ({_format_duration(total_minutes)} total)"
    return f"Custom 1 + 2 : {range_1} and {range_2}{total}"


def _format_window(
    start: str | None,
    end: str | None,
) -> tuple[str, str, int] | None:
    start_minutes = _parse_time(start)
    end_minutes = _parse_time(end)
    if start_minutes is None or end_minutes is None:
        return None

    duration_minutes = end_minutes - start_minutes
    if duration_minutes <= 0:
        duration_minutes += 24 * 60

    range_text = f"{_format_time(start_minutes)} to {_format_time(end_minutes)}"
    return range_text, _format_duration(duration_minutes), duration_minutes


def _parse_time(value: str | None) -> int | None:
    if value is None:
        return None

    try:
        hour_text, minute_text = value.split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError:
        return None

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def _format_time(minutes: int) -> str:
    hour, minute = divmod(minutes, 60)
    suffix = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12 or 12
    return f"{hour_12}:{minute:02d} {suffix}"


def _format_duration(minutes: int) -> str:
    hours, remaining_minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} {_plural('hour', hours)}")
    if remaining_minutes:
        parts.append(f"{remaining_minutes} {_plural('minute', remaining_minutes)}")
    return " ".join(parts) if parts else "0 minutes"


def _plural(word: str, value: int) -> str:
    return word if value == 1 else f"{word}s"
