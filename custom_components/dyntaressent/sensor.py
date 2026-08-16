"""Sensor-entiteiten voor de Essent dynamische tarieven."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CURRENCY_EURO, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import ELECTRICITY, GAS
from .coordinator import EnergyData, EssentConfigEntry, Slot
from .entity import EssentEntity
from .prices import effective_view, feed_in_value, feed_in_value_ex, slot_at as _slot_at

# Prijs-accessor: haalt uit een uur-tarief de gewenste waarde.
type PriceFn = Callable[[Slot], float]
# Metriek: berekent een sensorwaarde uit de data op een tijdstip.
type ValueFn = Callable[[EnergyData, datetime, PriceFn], float | None]
type AttrFn = Callable[[EnergyData, datetime, PriceFn], dict]

# Aantal decimalen waarmee prijzen worden getoond.
PRICE_PRECISION = 5


# --- Metriek-functies -------------------------------------------------------


def _current(data: EnergyData, now: datetime, price: PriceFn) -> float | None:
    slot = _slot_at(data.today, now)
    return price(slot) if slot else None


def _next_hour(data: EnergyData, now: datetime, price: PriceFn) -> float | None:
    slots = data.today + (data.tomorrow or [])
    slot = _slot_at(slots, now + timedelta(hours=1))
    return price(slot) if slot else None


def _previous_hour(data: EnergyData, now: datetime, price: PriceFn) -> float | None:
    slots = (data.yesterday or []) + data.today
    slot = _slot_at(slots, now - timedelta(hours=1))
    return price(slot) if slot else None


def _today_min(data: EnergyData, now: datetime, price: PriceFn) -> float | None:
    return min((price(s) for s in data.today), default=None)


def _today_max(data: EnergyData, now: datetime, price: PriceFn) -> float | None:
    return max((price(s) for s in data.today), default=None)


def _today_avg(data: EnergyData, now: datetime, price: PriceFn) -> float | None:
    if not data.today:
        return None
    return sum(price(s) for s in data.today) / len(data.today)


def _tomorrow_min(data: EnergyData, now: datetime, price: PriceFn) -> float | None:
    if not data.tomorrow:
        return None
    return min(price(s) for s in data.tomorrow)


def _tomorrow_max(data: EnergyData, now: datetime, price: PriceFn) -> float | None:
    if not data.tomorrow:
        return None
    return max(price(s) for s in data.tomorrow)


def _attributes(data: EnergyData, now: datetime, price: PriceFn) -> dict:
    """Rijke attributen op de 'huidige prijs' sensor (voor grafieken/automatiseringen)."""

    def series(slots: list[Slot]) -> list[dict]:
        return [
            {
                "start": s.start.isoformat(),
                "end": s.end.isoformat(),
                "price": round(price(s), PRICE_PRECISION),
            }
            for s in slots
        ]

    attrs: dict = {
        "unit": data.unit,
        "vat_percentage": data.vat_percentage,
        "today": series(data.today),
        "tomorrow": series(data.tomorrow) if data.tomorrow else None,
    }
    current = _slot_at(data.today, now)
    if current is not None:
        attrs["market_price"] = round(current.market, PRICE_PRECISION)
        attrs["purchase_fee"] = round(current.fee, PRICE_PRECISION)
        attrs["energy_tax"] = round(current.tax, PRICE_PRECISION)
    return attrs


# --- Descriptions -----------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class EssentSensorDescription(SensorEntityDescription):
    """Sensor-omschrijving met een waarde- en optionele attribuut-functie."""

    value_fn: ValueFn
    attr_fn: AttrFn | None = None


# (sleutel, label, icoon, waarde-functie, attribuut-functie)
_METRICS: tuple[tuple[str, str, str, ValueFn, AttrFn | None], ...] = (
    ("previous_hour", "vorig uur", "mdi:cash-clock", _previous_hour, None),
    ("current", "huidige prijs", "mdi:cash", _current, _attributes),
    ("next_hour", "volgend uur", "mdi:cash-clock", _next_hour, None),
    ("today_min", "vandaag laagste", "mdi:arrow-down-bold", _today_min, None),
    ("today_avg", "vandaag gemiddeld", "mdi:approximately-equal", _today_avg, None),
    ("today_max", "vandaag hoogste", "mdi:arrow-up-bold", _today_max, None),
    ("tomorrow_min", "morgen laagste", "mdi:arrow-down-bold-outline", _tomorrow_min, None),
    ("tomorrow_max", "morgen hoogste", "mdi:arrow-up-bold-outline", _tomorrow_max, None),
)

# (sleutel, label, prijs-accessor)
_BASES: tuple[tuple[str, str, PriceFn], ...] = (
    ("total", "all-in", lambda s: s.total),
    ("market", "beurs", lambda s: s.market),
)


class EssentPriceSensor(EssentEntity, SensorEntity):
    """Eén prijs-sensor voor een energietype + prijsbasis + metriek."""

    entity_description: EssentSensorDescription
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 4

    def __init__(
        self,
        coordinator,
        energy: str,
        basis_key: str,
        price_fn: PriceFn,
        description: EssentSensorDescription,
    ) -> None:
        super().__init__(coordinator, energy)
        self.entity_description = description
        self._price = price_fn
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{energy}_{basis_key}_{description.key}"
        )

    @property
    def native_unit_of_measurement(self) -> str:
        unit = self._data.unit if self._data else "kWh"
        return f"{CURRENCY_EURO}/{unit}"

    @property
    def native_value(self) -> float | None:
        data = self._data
        if data is None:
            return None
        data, now = effective_view(data, self._energy, dt_util.now())
        value = self.entity_description.value_fn(data, now, self._price)
        return None if value is None else round(value, PRICE_PRECISION)

    @property
    def extra_state_attributes(self) -> dict | None:
        data = self._data
        if data is None or self.entity_description.attr_fn is None:
            return None
        data, now = effective_view(data, self._energy, dt_util.now())
        return self.entity_description.attr_fn(data, now, self._price)


# --- Teruglever-sensoren (alleen elektra) -----------------------------------
# Data-gedreven: terugleververgoeding = beursprijs − inkoopvergoeding (opslag).
type FeedInFn = Callable[[EnergyData, datetime], float | None]


def _feedin_compensation(data: EnergyData, now: datetime) -> float | None:
    slot = _slot_at(data.today, now)
    return feed_in_value(slot) if slot else None


def _feedin_cost_now(data: EnergyData, now: datetime) -> float | None:
    slot = _slot_at(data.today, now)
    return max(0.0, -feed_in_value(slot)) if slot else None


def _feedin_cost_next(data: EnergyData, now: datetime) -> float | None:
    slot = _slot_at(data.today + (data.tomorrow or []), now + timedelta(hours=1))
    return max(0.0, -feed_in_value(slot)) if slot else None


def _negative_hours_today(data: EnergyData, now: datetime) -> float:
    return float(sum(1 for s in data.today if s.market < 0))


def _feedin_cost_hours_today(data: EnergyData, now: datetime) -> float:
    return float(sum(1 for s in data.today if feed_in_value(s) < 0))


@dataclass(frozen=True, kw_only=True)
class EssentFeedInSensorDescription(SensorEntityDescription):
    """Teruglever-sensor: prijs (€/kWh) of een uren-telling."""

    compute: FeedInFn
    is_hours: bool = False
    with_attrs: bool = False


_FEEDIN_SENSORS: tuple[EssentFeedInSensorDescription, ...] = (
    EssentFeedInSensorDescription(
        key="feedin_compensation_now",
        name="terugleververgoeding nu",
        icon="mdi:transmission-tower-export",
        suggested_display_precision=4,
        compute=_feedin_compensation,
        with_attrs=True,
    ),
    EssentFeedInSensorDescription(
        key="feedin_cost_now",
        name="terugleverkosten nu",
        icon="mdi:cash-minus",
        suggested_display_precision=4,
        compute=_feedin_cost_now,
    ),
    EssentFeedInSensorDescription(
        key="feedin_cost_next_hour",
        name="terugleverkosten volgend uur",
        icon="mdi:cash-minus",
        suggested_display_precision=4,
        compute=_feedin_cost_next,
    ),
    EssentFeedInSensorDescription(
        key="negative_hours_today",
        name="negatieve uren vandaag",
        icon="mdi:counter",
        suggested_display_precision=0,
        compute=_negative_hours_today,
        is_hours=True,
    ),
    EssentFeedInSensorDescription(
        key="feedin_cost_hours_today",
        name="uren terugleveren kost geld vandaag",
        icon="mdi:counter",
        suggested_display_precision=0,
        compute=_feedin_cost_hours_today,
        is_hours=True,
    ),
)


# --- Component-sensoren: energiebelasting & inkoopvergoeding (incl/excl btw) --


@dataclass(frozen=True, kw_only=True)
class EssentComponentSensorDescription(SensorEntityDescription):
    """Vaste prijscomponent van het huidige uur (€/eenheid)."""

    value_fn: Callable[[Slot], float]


# (basissleutel, label, icoon, incl-accessor, excl-accessor)
_COMPONENTS: tuple[tuple[str, str, str, PriceFn, PriceFn], ...] = (
    ("energy_tax", "energiebelasting", "mdi:bank", lambda s: s.tax, lambda s: s.tax_ex),
    ("purchase_fee", "inkoopvergoeding", "mdi:cash-plus", lambda s: s.fee, lambda s: s.fee_ex),
)


def _build_component_descriptions() -> list[EssentComponentSensorDescription]:
    out: list[EssentComponentSensorDescription] = []
    for base_key, label, icon, incl_fn, excl_fn in _COMPONENTS:
        out.append(
            EssentComponentSensorDescription(
                key=f"{base_key}_incl_vat",
                name=f"{label} incl btw",
                icon=icon,
                suggested_display_precision=5,
                value_fn=incl_fn,
            )
        )
        out.append(
            EssentComponentSensorDescription(
                key=f"{base_key}_excl_vat",
                name=f"{label} excl btw",
                icon=icon,
                suggested_display_precision=5,
                value_fn=excl_fn,
            )
        )
    return out


_COMPONENT_SENSORS = _build_component_descriptions()


class EssentComponentSensor(EssentEntity, SensorEntity):
    """Vaste prijscomponent (belasting/opslag) van het huidige uur, per energietype."""

    entity_description: EssentComponentSensorDescription
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator, energy: str, description: EssentComponentSensorDescription
    ) -> None:
        super().__init__(coordinator, energy)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{energy}_{description.key}"
        )

    @property
    def native_unit_of_measurement(self) -> str:
        unit = self._data.unit if self._data else "kWh"
        return f"{CURRENCY_EURO}/{unit}"

    @property
    def native_value(self) -> float | None:
        data = self._data
        if data is None:
            return None
        data, now = effective_view(data, self._energy, dt_util.now())
        slot = _slot_at(data.today, now)
        if slot is None:
            return None
        return round(self.entity_description.value_fn(slot), PRICE_PRECISION)


class EssentFeedInSensor(EssentEntity, SensorEntity):
    """Teruglever-gerelateerde sensor (altijd op het Stroom-device)."""

    entity_description: EssentFeedInSensorDescription
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, description: EssentFeedInSensorDescription) -> None:
        super().__init__(coordinator, ELECTRICITY)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_electricity_{description.key}"
        )

    @property
    def native_unit_of_measurement(self) -> str:
        if self.entity_description.is_hours:
            return UnitOfTime.HOURS
        unit = self._data.unit if self._data else "kWh"
        return f"{CURRENCY_EURO}/{unit}"

    @property
    def native_value(self) -> float | None:
        data = self._data
        if data is None:
            return None
        value = self.entity_description.compute(data, dt_util.now())
        if value is None:
            return None
        return round(value, 0 if self.entity_description.is_hours else PRICE_PRECISION)

    @property
    def extra_state_attributes(self) -> dict | None:
        if not self.entity_description.with_attrs or self._data is None:
            return None
        slot = _slot_at(self._data.today, dt_util.now())
        if slot is None:
            return None
        return {
            "market_price": round(slot.market, PRICE_PRECISION),
            "purchase_fee": round(slot.fee, PRICE_PRECISION),
            "threshold": round(slot.fee, PRICE_PRECISION),  # beursprijs ≤ opslag → kost geld
            "value_excl_vat": round(feed_in_value_ex(slot), PRICE_PRECISION),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EssentConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Bouw alle sensoren: energietype × prijsbasis × metriek, plus teruglever-sensoren."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = []
    for energy in (ELECTRICITY, GAS):
        for basis_key, basis_label, price_fn in _BASES:
            for key, label, icon, value_fn, attr_fn in _METRICS:
                description = EssentSensorDescription(
                    key=f"{basis_key}_{key}",
                    name=f"{basis_label} {label}",
                    icon=icon,
                    value_fn=value_fn,
                    attr_fn=attr_fn,
                )
                entities.append(
                    EssentPriceSensor(coordinator, energy, basis_key, price_fn, description)
                )

        # Component-sensoren (belasting + opslag, incl/excl btw) per energietype.
        entities.extend(
            EssentComponentSensor(coordinator, energy, description)
            for description in _COMPONENT_SENSORS
        )

    # Teruglever-sensoren zijn elektra-only.
    entities.extend(
        EssentFeedInSensor(coordinator, description) for description in _FEEDIN_SENSORS
    )

    async_add_entities(entities)
