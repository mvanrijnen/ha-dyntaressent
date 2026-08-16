# DynTarEssent — Dynamische Tarieven Essent

Publiceert de dynamische energietarieven van Essent (stroom + gas) als sensoren in
Home Assistant. **Geen account, login of API-sleutel nodig.**

## Wat je krijgt

- **Prijs-sensoren** per energietype (Stroom, Gas), zowel **all-in** als **beursprijs**:
  vorig uur, huidige prijs, volgend uur, en vandaag/morgen laagste/gemiddeld/hoogste.
- **Component-sensoren**: energiebelasting en inkoopvergoeding (opslag), incl. én excl. btw.
- **Teruglever-sensoren (elektra)**: terugleververgoeding, terugleverkosten en tellingen —
  volledig data-gedreven (drempel = beursprijs ≤ opslag), geen instellingen nodig.
- **Binary sensors** om direct op te schakelen: `prijs negatief` en
  `terugleveren kost geld` (nu / volgend uur) — ideaal voor ZeroExport of accu-sturing.
- Binary `morgen beschikbaar` per energietype.

De `huidige prijs`-sensoren dragen `today` / `tomorrow` arrays mee, klaar voor ApexCharts.

## Installatie

Voeg toe via HACS, herstart Home Assistant en configureer via
**Instellingen → Apparaten & Services → Integratie toevoegen → DynTarEssent**.

> Onofficieel. Haalt gegevens op van essent.nl. Geen affiliatie met Essent.
