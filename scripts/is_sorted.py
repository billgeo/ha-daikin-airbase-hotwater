"""Check string lists in JSON files are sorted case-insensitively."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any


def _tracked_json_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "*.json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(filename) for filename in result.stdout.splitlines()]


def _check_value(filename: Path, path: str, value: Any) -> list[str]:
    errors: list[str] = []
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            expected = sorted(value, key=str.casefold)
            if value != expected:
                errors.append(
                    f"{filename}:{path} is not sorted correctly\n"
                    f"  expected: {expected}\n"
                    f"  actual:   {value}"
                )
        for index, item in enumerate(value):
            errors.extend(_check_value(filename, f"{path}[{index}]", item))
    elif isinstance(value, dict):
        for key, item in value.items():
            next_path = f"{path}.{key}" if path else key
            errors.extend(_check_value(filename, next_path, item))
    return errors


def main() -> int:
    errors: list[str] = []
    for filename in _tracked_json_files():
        content = json.loads(filename.read_text(encoding="utf-8"))
        errors.extend(_check_value(filename, "", content))

    if errors:
        print("\n".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
