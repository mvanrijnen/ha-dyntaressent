"""De DynTarEssent integratie — Dynamische Tarieven Essent."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .coordinator import EssentConfigEntry, EssentDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Uren in de middag waarop de day-ahead prijzen van morgen doorgaans binnenkomen.
_AFTERNOON_RETRY_HOURS = [13, 14, 15, 16]


async def async_setup_entry(hass: HomeAssistant, entry: EssentConfigEntry) -> bool:
    """Zet een config entry op."""
    coordinator = EssentDataUpdateCoordinator(hass, entry)
    # 1) Ophalen bij opstarten van Home Assistant.
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _scheduled_refresh(_now) -> None:
        entry.async_create_background_task(
            hass, coordinator.async_request_refresh(), "dyntaressent_refresh"
        )

    # 2) Elk heel uur: zodat de "huidige prijs" netjes op het uur meerolt.
    entry.async_on_unload(
        async_track_time_change(hass, _scheduled_refresh, minute=0, second=10)
    )
    # 3) Extra pogingen in de middag tot de prijzen van morgen gepubliceerd zijn.
    entry.async_on_unload(
        async_track_time_change(
            hass,
            _scheduled_refresh,
            hour=_AFTERNOON_RETRY_HOURS,
            minute=30,
            second=10,
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EssentConfigEntry) -> bool:
    """Verwijder een config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
