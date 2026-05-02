"""Constants for the Daikin AirBase Hot Water integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "daikin_airbase_hotwater"
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL_SECONDS = 30

CONF_PORT = "port"

MANUFACTURER = "Daikin"
MODEL = "AirBase / BRP15B61 hot water"

MODE_OFF = "off"
MODE_AUTO = "auto"
MODE_MANUAL = "manual"

PLATFORMS = [
    Platform.WATER_HEATER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]
