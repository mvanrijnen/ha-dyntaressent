"""DataUpdateCoordinator die de Essent dynamische tarieven ophaalt."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_HEADERS,
    API_URL,
    DOMAIN,
    ELECTRICITY,
    GAS,
    GROUP_FEE,
    GROUP_MARKET,
    GROUP_TAX,
    LOGGER,
)

# Kale API-unit -> nette weergave.
UNIT_MAP = {"kWh": "kWh", "m3": "m³", "m³": "m³"}


@dataclass(slots=True)
class Slot:
    """Eén uur-tarief. Alle bedragen in euro, inclusief btw."""

    start: datetime
    end: datetime
    total: float  # all-in eindprijs (beurs + inkoop + belasting), incl. btw
    market: float  # kale beursprijs (EPEX), incl. btw
    market_ex: float  # kale beursprijs (EPEX), excl. btw
    fee: float  # inkoopvergoeding (opslag Essent), incl. btw
    fee_ex: float  # inkoopvergoeding, excl. btw
    tax: float  # energiebelasting, incl. btw
    tax_ex: float  # energiebelasting, excl. btw
    vat: float  # btw-deel van de totale prijs


@dataclass(slots=True)
class EnergyData:
    """Verwerkte tarieven voor één energietype."""

    unit: str
    vat_percentage: float
    today: list[Slot]
    tomorrow: list[Slot] | None
    yesterday: list[Slot] | None


type EssentData = dict[str, EnergyData]
type EssentConfigEntry = ConfigEntry[EssentDataUpdateCoordinator]


def _parse_dt(value: str) -> datetime:
    """Parse '2026-08-17T00:00:00' als lokale (Nederlandse) tijd."""
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Ongeldige datum/tijd: {value}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return parsed


def _group_amount(groups: list[dict], group_type: str, key: str = "amount") -> float:
    """Haal een bedrag van een group-type uit een uur-tarief.

    key="amount" is inclusief btw, key="amountEx" is exclusief btw.
    """
    for group in groups:
        if group.get("type") == group_type:
            return float(group.get(key) or 0.0)
    return 0.0


def _build_slots(tariffs: list[dict]) -> list[Slot]:
    slots: list[Slot] = []
    for tariff in tariffs:
        groups = tariff.get("groups", [])
        slots.append(
            Slot(
                start=_parse_dt(tariff["startDateTime"]),
                end=_parse_dt(tariff["endDateTime"]),
                total=float(tariff["totalAmount"]),
                market=_group_amount(groups, GROUP_MARKET),
                market_ex=_group_amount(groups, GROUP_MARKET, "amountEx"),
                fee=_group_amount(groups, GROUP_FEE),
                fee_ex=_group_amount(groups, GROUP_FEE, "amountEx"),
                tax=_group_amount(groups, GROUP_TAX),
                tax_ex=_group_amount(groups, GROUP_TAX, "amountEx"),
                vat=float(tariff.get("totalAmountVat") or 0.0),
            )
        )
    return slots


class EssentDataUpdateCoordinator(DataUpdateCoordinator[EssentData]):
    """Beheert het ophalen van de tarieven-array."""

    config_entry: EssentConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EssentConfigEntry) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            # Ophalen wordt door __init__.py aangestuurd (opstart, elk heel uur,
            # en extra pogingen in de middag). Dit interval is enkel een vangnet.
            update_interval=timedelta(hours=1),
        )
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> EssentData:
        try:
            async with self._session.get(
                API_URL,
                headers=API_HEADERS,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Fout bij ophalen Essent-tarieven: {err}") from err

        by_date = {day["date"]: day for day in payload.get("prices", [])}
        now = dt_util.now()
        today_key = now.strftime("%Y-%m-%d")
        tomorrow_key = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_key = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        result: EssentData = {}
        for energy in (ELECTRICITY, GAS):
            today_block = (by_date.get(today_key) or {}).get(energy)
            if not today_block or not today_block.get("tariffs"):
                continue

            tomorrow_block = (by_date.get(tomorrow_key) or {}).get(energy)
            has_tomorrow = bool(tomorrow_block and tomorrow_block.get("tariffs"))
            yesterday_block = (by_date.get(yesterday_key) or {}).get(energy)
            has_yesterday = bool(yesterday_block and yesterday_block.get("tariffs"))

            result[energy] = EnergyData(
                unit=UNIT_MAP.get(
                    today_block.get("unitOfMeasurement", ""),
                    today_block.get("unitOfMeasurement", ""),
                ),
                vat_percentage=float(today_block.get("vatPercentage") or 0),
                today=_build_slots(today_block["tariffs"]),
                tomorrow=_build_slots(tomorrow_block["tariffs"]) if has_tomorrow else None,
                yesterday=_build_slots(yesterday_block["tariffs"]) if has_yesterday else None,
            )

        if not result:
            raise UpdateFailed("Geen tarieven voor vandaag ontvangen")

        return result
