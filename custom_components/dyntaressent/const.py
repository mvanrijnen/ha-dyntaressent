"""Constanten voor de DynTarEssent integratie (Dynamische Tarieven Essent)."""

from __future__ import annotations

import logging

DOMAIN = "dyntaressent"
NAME = "DynTarEssent"
MANUFACTURER = "Essent"

LOGGER = logging.getLogger(__package__)

# Publieke, token-vrije proxy. Vereist enkel deze header.
API_URL = "https://www.essent.nl/api/public/dynamicpricing/dynamic-prices/v1"
API_HEADERS = {"x-request-origin": "client"}

# Energietypes zoals de API ze levert.
ELECTRICITY = "electricity"
GAS = "gas"

# Weergavenaam per energietype (gebruikt als device-naam).
ENERGY_NAMES = {
    ELECTRICITY: "Stroom",
    GAS: "Gas",
}

# Group-types binnen een uur-tarief.
GROUP_MARKET = "MARKET_PRICE"
GROUP_FEE = "PURCHASING_FEE"
GROUP_TAX = "TAX"
