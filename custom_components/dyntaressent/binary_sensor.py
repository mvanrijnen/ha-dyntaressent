"""Binary sensors: morgen beschikbaar + teruglever-/negatieve-prijs detectie."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import ELECTRICITY, GAS
from .coordinator import EnergyData, EssentConfigEntry
from .entity import EssentEntity
from .prices import feed_in_value, slot_at

# Beslisfunctie: (data, nu) -> aan/uit (None = onbekend)
type StateFn = Callable[[EnergyData, datetime], bool | None]


# --- Slot-selectie ----------------------------------------------------------


def _now_slot(data: EnergyData, now: datetime):
    return slot_at(data.today, now)


def _next_slot(data: EnergyData, now: datetime):
    return slot_at(data.today + (data.tomorrow or []), now + timedelta(hours=1))


def _prev_slot(data: EnergyData, now: datetime):
    return slot_at((data.yesterday or []) + data.today, now - timedelta(hours=1))


# --- Beslisfuncties ---------------------------------------------------------
# "prijs negatief" = kale beursprijs (incl. btw) onder nul.


def _neg_now(data, now):
    slot = _now_slot(data, now)
    return None if slot is None else slot.market < 0


def _neg_prev(data, now):
    slot = _prev_slot(data, now)
    return None if slot is None else slot.market < 0


def _neg_next(data, now):
    slot = _next_slot(data, now)
    return None if slot is None else slot.market < 0


# "terugleveren kost geld" = beursprijs ≤ opslag (terugleververgoeding onder nul).


def _feedin_cost_now(data, now):
    slot = _now_slot(data, now)
    return None if slot is None else feed_in_value(slot) < 0


def _feedin_cost_next(data, now):
    slot = _next_slot(data, now)
    return None if slot is None else feed_in_value(slot) < 0


@dataclass(frozen=True, kw_only=True)
class EssentBinaryDescription(BinarySensorEntityDescription):
    """Binary sensor met een beslisfunctie."""

    state_fn: StateFn


_BINARY_SENSORS: tuple[EssentBinaryDescription, ...] = (
    EssentBinaryDescription(
        key="price_negative_now",
        name="prijs negatief nu",
        icon="mdi:cash-minus",
        state_fn=_neg_now,
    ),
    EssentBinaryDescription(
        key="price_negative_previous_hour",
        name="prijs negatief vorig uur",
        icon="mdi:cash-minus",
        state_fn=_neg_prev,
    ),
    EssentBinaryDescription(
        key="price_negative_next_hour",
        name="prijs negatief volgend uur",
        icon="mdi:cash-minus",
        state_fn=_neg_next,
    ),
    EssentBinaryDescription(
        key="feedin_costs_money_now",
        name="terugleveren kost geld nu",
        icon="mdi:transmission-tower-export",
        state_fn=_feedin_cost_now,
    ),
    EssentBinaryDescription(
        key="feedin_costs_money_next_hour",
        name="terugleveren kost geld volgend uur",
        icon="mdi:transmission-tower-export",
        state_fn=_feedin_cost_next,
    ),
)


class EssentTomorrowAvailable(EssentEntity, BinarySensorEntity):
    """Aan zodra de day-ahead tarieven van morgen beschikbaar zijn."""

    _attr_name = "morgen beschikbaar"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, energy: str) -> None:
        super().__init__(coordinator, energy)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{energy}_tomorrow_available"
        )

    @property
    def is_on(self) -> bool:
        return bool(self._data and self._data.tomorrow)


class EssentFeedInBinary(EssentEntity, BinarySensorEntity):
    """Negatieve-prijs / teruglever-detectie (elektra). Direct schakelbaar."""

    entity_description: EssentBinaryDescription

    def __init__(self, coordinator, description: EssentBinaryDescription) -> None:
        super().__init__(coordinator, ELECTRICITY)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_electricity_{description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        data = self._data
        if data is None:
            return None
        return self.entity_description.state_fn(data, dt_util.now())


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EssentConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    entities: list[BinarySensorEntity] = [
        EssentTomorrowAvailable(coordinator, energy) for energy in (ELECTRICITY, GAS)
    ]
    # Teruglever-/negatieve-prijs binaries zijn elektra-only.
    entities.extend(
        EssentFeedInBinary(coordinator, description) for description in _BINARY_SENSORS
    )
    async_add_entities(entities)
