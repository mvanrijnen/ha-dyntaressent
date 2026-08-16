"""Basis-entiteit met device-info voor de Essent integratie."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENERGY_NAMES, MANUFACTURER, NAME
from .coordinator import EnergyData, EssentDataUpdateCoordinator


class EssentEntity(CoordinatorEntity[EssentDataUpdateCoordinator]):
    """Gedeelde basis: koppelt de entiteit aan een device per energietype."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EssentDataUpdateCoordinator, energy: str) -> None:
        super().__init__(coordinator)
        self._energy = energy
        entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{energy}")},
            name=f"{NAME} {ENERGY_NAMES[energy]}",
            manufacturer=MANUFACTURER,
            model="Dynamische Tarieven",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def _data(self) -> EnergyData | None:
        return self.coordinator.data.get(self._energy)

    @property
    def available(self) -> bool:
        return super().available and self._data is not None
