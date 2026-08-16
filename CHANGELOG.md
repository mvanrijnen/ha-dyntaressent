# Changelog

Alle noemenswaardige wijzigingen aan dit project worden hier vastgelegd.

Het formaat is gebaseerd op [Keep a Changelog](https://keepachangelog.com/nl/1.1.0/),
en dit project volgt [Semantic Versioning](https://semver.org/lang/nl/).

## [1.4.1] - 2026-08-17

### Fixed
- Gas toont weer de **daadwerkelijk op dat moment geldende prijs** (bijv. vóór 06:00 de
  nog lopende gasdag), in plaats van alvast de headline-prijs van de nieuwe gasdag zoals
  in 1.4.0. De gasprijs verspringt om 06:00; de sensor volgt de op dat moment geldende
  gasdag. Draait de gasdag-benadering uit 1.4.0 terug.

## [1.4.0] - 2026-08-17

### Fixed
- **Gasprijs volgt nu de gasdag (06:00–06:00)** in plaats van het letterlijke klokuur.
  Gas is een dagprijs die om 06:00 verspringt; tussen 00:00 en 06:00 toonden de
  gas-sensoren nog de prijs van de vórige gasdag, waardoor ze afweken van essent.nl.
  Nu komen de gas-sensoren overeen met de website. Elektra blijft per uur.

## [1.3.0] - 2026-08-17

### Changed
- Teruglever-model is nu volledig **data-gedreven**: terugleververgoeding =
  beursprijs − inkoopvergoeding (opslag). De drempel voor "terugleveren kost geld"
  is daarmee `beursprijs ≤ opslag`, rechtstreeks uit de data — btw-onafhankelijk.
- `prijs negatief` (beursprijs < 0) en `terugleveren kost geld` (beursprijs ≤ opslag)
  zijn nu betekenisvol verschillende drempels.

### Removed
- Options-flow voor het teruglever-model (btw-basis + vaste terugleverkosten). Niet
  langer nodig omdat de drempel uit de data komt; er valt niets meer te configureren.

## [1.2.0] - 2026-08-17

### Added
- Component-sensoren per energietype voor **energiebelasting** en **inkoopvergoeding
  (opslag)**, zowel inclusief als exclusief btw.

## [1.1.0] - 2026-08-16

### Added
- Teruglever-/negatieve-prijs entiteiten (elektra), bedoeld om direct op te schakelen:
  - Binary sensors: `prijs negatief nu/vorig uur/volgend uur`,
    `terugleveren kost geld nu/volgend uur`.
  - Sensors: `terugleververgoeding nu`, `terugleverkosten nu/volgend uur`,
    `negatieve uren vandaag`, `uren terugleveren kost geld vandaag`.

## [1.0.0] - 2026-08-16

### Added
- Eerste versie. Haalt de dynamische tarieven van Essent (stroom + gas) op —
  geen account of API-sleutel nodig.
- Prijs-sensoren per energietype (Stroom, Gas) en per prijsbasis (all-in, beurs):
  vorig uur, huidige prijs, volgend uur, vandaag laagste/gemiddeld/hoogste,
  morgen laagste/hoogste.
- Binary sensor `morgen beschikbaar` per energietype.
- `huidige prijs`-sensoren met `today`/`tomorrow` arrays (voor ApexCharts) + breakdown.
- Ophalen bij opstart, elk heel uur, en extra pogingen in de middag tot de prijzen
  van morgen gepubliceerd zijn.
- Config-flow (UI-installatie) en HACS-ondersteuning.

[1.3.0]: https://github.com/mvanrijnen/ha-dyntaressent/releases/tag/v1.3.0
[1.2.0]: https://github.com/mvanrijnen/ha-dyntaressent/releases/tag/v1.2.0
[1.1.0]: https://github.com/mvanrijnen/ha-dyntaressent/releases/tag/v1.1.0
[1.0.0]: https://github.com/mvanrijnen/ha-dyntaressent/releases/tag/v1.0.0
