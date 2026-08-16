"""Gedeelde prijs- en teruglever-helpers."""

from __future__ import annotations

from datetime import datetime

from .const import GAS
from .coordinator import EnergyData, Slot

# De Nederlandse "gasdag" loopt van 06:00 tot 06:00. Gas is per gasdag constant.
GAS_DAY_START_HOUR = 6


def slot_at(slots: list[Slot], moment: datetime) -> Slot | None:
    """Vind het uur-slot dat `moment` bevat."""
    for slot in slots:
        if slot.start <= moment < slot.end:
            return slot
    return None


def effective_view(data: EnergyData, energy: str, now: datetime) -> tuple[EnergyData, datetime]:
    """Pas data + referentietijd aan per energietype.

    Elektra: ongewijzigd (echt per uur). Gas: gebruik de gasdag (prijs vanaf 06:00,
    zoals de website), zodat de tussen 00:00–06:00 nog geldende prijs van de vórige
    gasdag niet meer als 'vandaag' wordt getoond. Omdat gas per gasdag constant is,
    volstaat het de slots vanaf 06:00 te nemen en het referentiemoment op het midden
    van de dag te zetten.
    """
    if energy != GAS:
        return data, now

    def gas_day(slots: list[Slot] | None) -> list[Slot] | None:
        if not slots:
            return slots
        filtered = [s for s in slots if s.start.hour >= GAS_DAY_START_HOUR]
        return filtered or slots

    adjusted = EnergyData(
        unit=data.unit,
        vat_percentage=data.vat_percentage,
        today=gas_day(data.today),
        tomorrow=gas_day(data.tomorrow),
        yesterday=gas_day(data.yesterday),
    )
    noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
    return adjusted, noon


def feed_in_value(slot: Slot) -> float:
    """Netto terugleververgoeding (incl. btw) voor een uur (€/kWh).

    = beursprijs − inkoopvergoeding (de opslag die Essent ook op teruglevering
    inhoudt). Negatief = terugleveren kost geld. De drempel is dus volledig
    data-gedreven: beursprijs ≤ opslag. Geen gebruikersconfiguratie nodig.
    """
    return slot.market - slot.fee


def feed_in_value_ex(slot: Slot) -> float:
    """Netto terugleververgoeding excl. btw (€/kWh)."""
    return slot.market_ex - slot.fee_ex
