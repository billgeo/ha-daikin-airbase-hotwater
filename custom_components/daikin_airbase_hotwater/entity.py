"""Base entities for Daikin AirBase Hot Water."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PORT, DEFAULT_PORT, DOMAIN, MANUFACTURER, MODEL
from .coordinator import DaikinAirBaseHotWaterCoordinator


class DaikinAirBaseHotWaterEntity(CoordinatorEntity[DaikinAirBaseHotWaterCoordinator]):
    """Base entity for AirBase hot water devices."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DaikinAirBaseHotWaterCoordinator,
        translation_key: str,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{translation_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        host = self.coordinator.config_entry.data[CONF_HOST]
        port = self.coordinator.config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.unique_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name="Daikin AirBase Hot Water",
            configuration_url=f"http://{host}"
            if port == DEFAULT_PORT
            else f"http://{host}:{port}",
        )
