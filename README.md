# DynTarEssent — Dynamische Tarieven Essent

[![Validate](https://github.com/mvanrijnen/ha-dyntaressent/actions/workflows/validate.yml/badge.svg)](https://github.com/mvanrijnen/ha-dyntaressent/actions/workflows/validate.yml)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mvanrijnen&repository=ha-dyntaressent&category=integration)

Home Assistant integratie die de dynamische energietarieven van
[Essent](https://www.essent.nl/dynamische-tarieven) als sensoren publiceert.
**Geen account, login of API-sleutel nodig.**

## Data

De integratie levert **gisteren, vandaag en morgen** (24 uur-slots per dag) voor zowel
**stroom** als **gas**. De tarieven zijn de volledige eindprijs: beursprijs (EPEX) +
inkoopvergoeding + energiebelasting, inclusief 21% btw. De prijzen van morgen komen 's
middags binnen (day-ahead, doorgaans tussen 13:00 en 16:00).

**Stroom** is per uur; **gas** is een dagprijs die de Nederlandse **gasdag** (06:00–06:00)
volgt. De gas-sensoren tonen daarom de gasdag-prijs van de dag, gelijk aan wat essent.nl toont.

## Ophaalschema

- **Bij het starten** van Home Assistant.
- **Elk heel uur** (zodat "huidige prijs" netjes op het uur meerolt).
- **Extra pogingen om 13:30 / 14:30 / 15:30 / 16:30** tot de prijzen van morgen zijn gepubliceerd.

## Sensoren

Per energietype — device **DynTarEssent Stroom** en **DynTarEssent Gas** — en per prijsbasis
(**all-in** en **beurs**):

| Sensor | Betekenis |
| --- | --- |
| `… vorig uur` | Prijs van het vorige uur |
| `… huidige prijs` | Prijs van het huidige uur — met attributen (zie onder) |
| `… volgend uur` | Prijs van het eerstvolgende uur |
| `… vandaag laagste` | Laagste prijs vandaag |
| `… vandaag gemiddeld` | Gemiddelde prijs vandaag |
| `… vandaag hoogste` | Hoogste prijs vandaag |
| `… morgen laagste` | Laagste prijs morgen (leeg tot gepubliceerd) |
| `… morgen hoogste` | Hoogste prijs morgen (leeg tot gepubliceerd) |

Plus per energietype een **binary sensor** `morgen beschikbaar` (aan zodra morgen gepubliceerd is).

En per energietype de vaste prijscomponenten van het huidige uur, **incl. én excl. btw**:

| Sensor | Betekenis |
| --- | --- |
| `energiebelasting incl btw` / `… excl btw` | Energiebelasting per kWh/m³ |
| `inkoopvergoeding incl btw` / `… excl btw` | Opslag van Essent per kWh/m³ |

> Deze componenten zijn constant per dag; alleen de beursprijs varieert per uur.

> "all-in" = de volledige eindprijs; "beurs" = de kale EPEX-beursprijs (handig als je zelf
> je opslag/belasting rekent). Eenheid: €/kWh (stroom) of €/m³ (gas).

### Attributen op "huidige prijs"

De `huidige prijs`-sensoren dragen de volledige dag-arrays mee, klaar voor
[ApexCharts](https://github.com/RomRider/apexcharts-card):

- `today` — lijst van `{ start, end, price }`
- `tomorrow` — idem (of `null` tot gepubliceerd)
- `market_price`, `purchase_fee`, `energy_tax` — opbouw van het huidige uur
- `unit`, `vat_percentage`

## Teruglevering & negatieve prijzen (alleen elektra)

Bij negatieve beursprijzen kost terugleveren geld in plaats van dat het oplevert. Deze
entiteiten (op device **DynTarEssent Stroom**) zijn bedoeld om **direct op te schakelen** —
bv. ZeroExport op een PV-omvormer inschakelen of een accu geforceerd laten laden.

**Binary sensors** (direct bruikbaar als trigger)

| Entiteit | Aan wanneer |
| --- | --- |
| `prijs negatief nu` | beursprijs huidige uur < 0 |
| `prijs negatief vorig uur` | beursprijs vorige uur < 0 |
| `prijs negatief volgend uur` | beursprijs volgende uur < 0 |
| `terugleveren kost geld nu` | beursprijs huidige uur ≤ opslag |
| `terugleveren kost geld volgend uur` | beursprijs volgende uur ≤ opslag |

**Sensors**

| Entiteit | Waarde |
| --- | --- |
| `terugleververgoeding nu` | €/kWh die je krijgt voor export dit uur (kan negatief) |
| `terugleverkosten nu` | €/kWh die export je kost (0 als het niets kost) |
| `terugleverkosten volgend uur` | idem, volgende uur |
| `negatieve uren vandaag` | aantal uren met beursprijs < 0 |
| `uren terugleveren kost geld vandaag` | aantal uren dat export geld kost |

### Het teruglever-model (data-gedreven, geen instellingen nodig)

De terugleververgoeding wordt volledig uit de data afgeleid:

> **terugleververgoeding = beursprijs − inkoopvergoeding (opslag)**

Essent houdt zijn opslag ook in op wat je teruglevert, dus je verdient alleen als de
beursprijs boven de opslag ligt. De drempel is daarom **beursprijs ≤ opslag** → dan kost
terugleveren geld. Die opslag zit gewoon in de data (`inkoopvergoeding`), dus er is niets
te configureren.

- Deze drempel is **btw-onafhankelijk** (beide kanten × 1,21), dus de trigger is eenduidig.
- `prijs negatief` (beursprijs < 0) en `terugleveren kost geld` (beursprijs < opslag) zijn nu
  verschillende drempels — de laatste triggert eerder. `negatieve uren vandaag` ≤
  `uren terugleveren kost geld vandaag`.
- De `terugleververgoeding nu`-sensor toont in de attributen `market_price`, `purchase_fee`
  (= de drempel) en `value_excl_vat`.

### Voorbeeld: ZeroExport / accu forceren bij negatieve prijs

```yaml
automation:
  - alias: ZeroExport aan bij negatieve teruglevering
    trigger:
      - platform: state
        entity_id: binary_sensor.dyntaressent_stroom_terugleveren_kost_geld_nu
        to: "on"
    action:
      - service: switch.turn_on
        target: { entity_id: switch.omvormer_zero_export }
  - alias: ZeroExport uit als teruglevering weer loont
    trigger:
      - platform: state
        entity_id: binary_sensor.dyntaressent_stroom_terugleveren_kost_geld_nu
        to: "off"
    action:
      - service: switch.turn_off
        target: { entity_id: switch.omvormer_zero_export }
```

## Installatie (HACS)

**Snel — via de knop** (vereist dat HACS al geïnstalleerd is):

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mvanrijnen&repository=ha-dyntaressent&category=integration)

Klik de knop → HACS opent op jouw Home Assistant met deze repo al ingevuld → **Download**,
en herstart Home Assistant. Voeg daarna de integratie toe met de knop hieronder (of via
**Instellingen → Apparaten & Services → Integratie toevoegen** → *DynTarEssent*):

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dyntaressent)

**Handmatig:**

1. HACS → ⋮ → **Custom repositories** → `https://github.com/mvanrijnen/ha-dyntaressent`, categorie **Integration**.
2. Installeer **Dynamische Tarieven Essent** en herstart Home Assistant.
3. **Instellingen → Apparaten & Services → Integratie toevoegen** → zoek *DynTarEssent*.

Of handmatig: kopieer `custom_components/dyntaressent/` naar je Home Assistant
`config/custom_components/` map en herstart.

## Voorbeeld: ApexCharts-kaart

```yaml
type: custom:apexcharts-card
header:
  title: Stroomprijs vandaag (all-in)
graph_span: 24h
series:
  - entity: sensor.dyntaressent_stroom_all_in_huidige_prijs
    type: column
    data_generator: |
      return entity.attributes.today.map(s => [new Date(s.start).getTime(), s.price]);
```

## Voorbeeld: automatisering (goedkoop uur)

```yaml
trigger:
  - platform: numeric_state
    entity_id: sensor.dyntaressent_stroom_all_in_huidige_prijs
    below: 0.20
action:
  - service: notify.mobile_app
    data:
      message: "Stroom is nu goedkoop: {{ states('sensor.dyntaressent_stroom_all_in_huidige_prijs') }} €/kWh"
```

## Disclaimer

Onofficieel. Haalt gegevens op van essent.nl; Essent kan dit zonder aankondiging
wijzigen. Geen affiliatie met Essent.

## Licentie

[MIT](LICENSE) © Maurits van Rijnen
