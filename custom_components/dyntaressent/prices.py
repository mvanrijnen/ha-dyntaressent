"""Gedeelde prijs- en teruglever-helpers."""

from __future__ import annotations

from datetime import datetime

from .coordinator import Slot


def slot_at(slots: list[Slot], moment: datetime) -> Slot | None:
    """Vind het uur-slot dat `moment` bevat.

    Werkt voor zowel elektra (echt per uur) als gas: de API levert gas ook als
    uur-slots, waarbij de prijs om 06:00 verspringt (Nederlandse gasdag, 06:00–06:00).
    Zo toont de sensor altijd de op dat moment daadwerkelijk geldende prijs.
    """
    for slot in slots:
        if slot.start <= moment < slot.end:
            return slot
    return None


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
