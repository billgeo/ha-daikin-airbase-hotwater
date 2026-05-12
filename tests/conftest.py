"""Test stubs for Home Assistant imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _register_module(name: str) -> ModuleType:
    """Register a stub module and attach it to its parent."""
    module = ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module
    if "." in name:
        parent_name, child_name = name.rsplit(".", 1)
        setattr(sys.modules[parent_name], child_name, module)
    return module


homeassistant = _register_module("homeassistant")
components = _register_module("homeassistant.components")
helpers = _register_module("homeassistant.helpers")
util = _register_module("homeassistant.util")

const = _register_module("homeassistant.const")
const.CONF_HOST = "host"


class Platform:
    """Minimal Home Assistant platform constants."""

    WATER_HEATER = "water_heater"
    SENSOR = "sensor"
    SWITCH = "switch"
    NUMBER = "number"
    SELECT = "select"


class UnitOfEnergy:
    """Minimal energy unit constants."""

    KILO_WATT_HOUR = "kWh"


class UnitOfPower:
    """Minimal power unit constants."""

    WATT = "W"


class UnitOfTemperature:
    """Minimal temperature unit constants."""

    CELSIUS = "C"


const.Platform = Platform
const.UnitOfEnergy = UnitOfEnergy
const.UnitOfPower = UnitOfPower
const.UnitOfTemperature = UnitOfTemperature

core = _register_module("homeassistant.core")


class HomeAssistant:
    """Minimal Home Assistant marker class."""


core.HomeAssistant = HomeAssistant

aiohttp_client = _register_module("homeassistant.helpers.aiohttp_client")


def async_get_clientsession(hass: Any) -> Any:
    """Return the fake session attached to hass."""
    return getattr(hass, "session", None)


aiohttp_client.async_get_clientsession = async_get_clientsession

update_coordinator = _register_module("homeassistant.helpers.update_coordinator")


class UpdateFailed(Exception):
    """Minimal update failure exception."""


class DataUpdateCoordinator:
    """Minimal DataUpdateCoordinator for unit tests."""

    def __init__(
        self,
        hass: Any,
        *,
        logger: Any,
        name: str,
        update_interval: Any,
    ) -> None:
        """Initialise coordinator metadata."""
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    def __class_getitem__(cls, item: Any) -> type[DataUpdateCoordinator]:
        """Support generic subscription in integration code."""
        return cls

    async def async_config_entry_first_refresh(self) -> None:
        """Fetch initial data."""
        self.data = await self._async_update_data()

    async def async_request_refresh(self) -> None:
        """Refresh data."""
        self.data = await self._async_update_data()


class CoordinatorEntity:
    """Minimal CoordinatorEntity for unit tests."""

    def __init__(self, coordinator: Any) -> None:
        """Store the coordinator."""
        self.coordinator = coordinator

    def __class_getitem__(cls, item: Any) -> type[CoordinatorEntity]:
        """Support generic subscription in integration code."""
        return cls

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return True


update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed
update_coordinator.CoordinatorEntity = CoordinatorEntity

config_entries = _register_module("homeassistant.config_entries")


class ConfigEntry:
    """Minimal ConfigEntry marker class."""


class ConfigFlow:
    """Minimal ConfigFlow for unit tests."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Accept Home Assistant's domain keyword."""
        super().__init_subclass__()

    async def async_set_unique_id(self, unique_id: str) -> None:
        """Store the unique ID."""
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        """Record duplicate check."""
        self.abort_checked = True

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
        """Return a create-entry flow result."""
        return {"type": "create_entry", **kwargs}

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        """Return a form flow result."""
        return {"type": "form", **kwargs}


config_entries.ConfigEntry = ConfigEntry
config_entries.ConfigFlow = ConfigFlow

data_entry_flow = _register_module("homeassistant.data_entry_flow")
data_entry_flow.FlowResult = dict[str, Any]

entity_platform = _register_module("homeassistant.helpers.entity_platform")
entity_platform.AddEntitiesCallback = object

typing_module = _register_module("homeassistant.helpers.typing")
typing_module.StateType = object

device_registry = _register_module("homeassistant.helpers.device_registry")


class DeviceInfo(dict):
    """Simple mapping-backed DeviceInfo."""

    def __init__(self, **kwargs: Any) -> None:
        """Store device info fields."""
        super().__init__(kwargs)


device_registry.DeviceInfo = DeviceInfo


@dataclass(frozen=True, kw_only=True)
class EntityDescription:
    """Shared entity description fields used in tests."""

    key: str
    translation_key: str | None = None
    device_class: str | None = None
    native_unit_of_measurement: str | None = None
    state_class: str | None = None
    suggested_display_precision: int | None = None
    native_min_value: float | None = None
    native_max_value: float | None = None
    native_step: float | None = None
    mode: str | None = None


sensor = _register_module("homeassistant.components.sensor")


class SensorDeviceClass:
    """Minimal sensor device class constants."""

    ENERGY = "energy"
    POWER = "power"
    TEMPERATURE = "temperature"


class SensorStateClass:
    """Minimal sensor state class constants."""

    MEASUREMENT = "measurement"
    TOTAL_INCREASING = "total_increasing"


class SensorEntity:
    """Minimal sensor entity."""


sensor.SensorDeviceClass = SensorDeviceClass
sensor.SensorStateClass = SensorStateClass
sensor.SensorEntity = SensorEntity
sensor.SensorEntityDescription = EntityDescription

switch = _register_module("homeassistant.components.switch")


class SwitchEntity:
    """Minimal switch entity."""


switch.SwitchEntity = SwitchEntity
switch.SwitchEntityDescription = EntityDescription

number = _register_module("homeassistant.components.number")


class NumberEntity:
    """Minimal number entity."""


class NumberMode:
    """Minimal number mode constants."""

    BOX = "box"
    SLIDER = "slider"


number.NumberEntity = NumberEntity
number.NumberEntityDescription = EntityDescription
number.NumberMode = NumberMode

select = _register_module("homeassistant.components.select")


class SelectEntity:
    """Minimal select entity."""


select.SelectEntity = SelectEntity

water_heater = _register_module("homeassistant.components.water_heater")


class WaterHeaterEntity:
    """Minimal water heater entity."""


class WaterHeaterEntityFeature:
    """Minimal water heater feature constants."""

    OPERATION_MODE = 1


water_heater.WaterHeaterEntity = WaterHeaterEntity
water_heater.WaterHeaterEntityFeature = WaterHeaterEntityFeature

dt = _register_module("homeassistant.util.dt")
dt.now = lambda: datetime.now(UTC)

voluptuous = _register_module("voluptuous")


class _Marker:
    """Minimal voluptuous schema marker."""

    def __init__(self, key: str, *, default: Any = None) -> None:
        """Store marker values."""
        self.key = key
        self.default = default

    def __hash__(self) -> int:
        """Return a stable hash."""
        return hash((type(self), self.key, self.default))


class Schema:
    """Minimal voluptuous schema."""

    def __init__(self, schema: dict[Any, Any]) -> None:
        """Store schema fields."""
        self.schema = schema

    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return input data unchanged."""
        return data


voluptuous.Required = _Marker
voluptuous.Optional = _Marker
voluptuous.Schema = Schema
