# Rotation scoring algorithm: implementation and references

This document is the detailed technical companion to
[`data-science-approach.md`](data-science-approach.md). That file explains
*why* the project is built this way and what was deliberately left out.
This file explains *how* each step actually computes its numbers, with the
equations, parameter choices and literature behind them, so a judge or a
teammate can check the maths against the code in `backend/app/engine/`.

Every equation below matches a specific function. Where a step is this
project's own construction rather than a published method, that is stated
plainly rather than implied.

## 1. Pipeline overview

```
farm (lat, lon) + priority weights + optional current rotation
  │
  ├─ NASA POWER (fetch_power_daily)      daily weather, 1 year
  ├─ ISRIC SoilGrids v2.0 (fetch_soilgrids)   topsoil properties, one point
  │
  ▼
reference evapotranspiration (ET0), FAO-56 Penman-Monteith
  ▼
climate suitability filter → crop pool restricted to what can grow here
  ▼
candidate generation → all 3-year sequences from that pool
  ▼
hard agronomic filter → drop sequences that repeat a crop family too soon
  ▼
per-year scoring (soil, water, resilience, revenue) → weighted sum → RSI
  ▼
rank candidates by RSI, attach impact metrics vs. a monoculture baseline,
attach plain-language explanations and standing risk/gap caveats
```

## 2. Inputs

### 2.1 NASA POWER (`backend/app/data/nasa_power.py`)

Daily point data from the POWER Daily API (`AG` community), no API key
required. Fields pulled, and what each feeds:

| Field | Used for |
|---|---|
| `T2M`, `T2M_MAX`, `T2M_MIN` | ET0 (Penman-Monteith), climate suitability, frost check |
| `RH2M` | ET0 (actual vapour pressure) |
| `WS2M` | ET0 (aerodynamic term); already reported at 2 m, matching FAO-56's reference height |
| `ALLSKY_SFC_SW_DWN` | ET0 (net shortwave radiation) |
| `PRECTOTCORR` | water-balance baseline (seasonal rainfall) |
| `GWETROOT`, `GWETTOP` | root-zone/surface soil wetness, used as a SMAP stand-in (see §9) |

A fill value of `-999` from POWER is converted to a missing value before
anything downstream touches it.

### 2.2 ISRIC SoilGrids v2.0 (`backend/app/data/soilgrids.py`)

Topsoil (0–5 cm) mean values for `clay`, `sand`, `phh2o`, `soc`, queried for
a single point. SoilGrids reports these in tenths of their conventional
unit; the client multiplies by 0.1 to get g/kg (organic carbon) and percent
(clay, sand, pH). Only `soc` (organic carbon) is currently used by the
scoring engine; clay, sand and pH are fetched but not yet wired into a
score (see §13).

### 2.3 Crop dataset (`data/crops.json`)

A hand-curated table of ten crops (maize, soybean, winter wheat, oats,
cereal rye as a cover crop, alfalfa, lentil, chickpea, rice, sorghum), each
with a `flood_irrigated` flag where relevant (currently only rice, see
§12) plus:

- `crop_family` (for the agronomic hard filter)
- `nitrogen_balance_kg_ha` (net soil nitrogen credit or debit for the year)
- `kc_ini`, `kc_mid`, `kc_end`, `season_length_days` (for ET0 → ETc)
- `min_temp_c`, `max_temp_c` (climate suitability bounds)
- `root_type`, `root_depth_class` (soil-score root-diversity bonus)
- `drought_tolerance` (resilience score)
- `role`, `has_market_revenue`, `typical_yield_t_ha` (erosion and revenue
  proxies)
- `source`, a free-text citation for every number in the row, including
  explicit notes where published figures disagreed across studies.

Primary sources: FAO Irrigation and Drainage Paper 56 (Allen et al.,
1998); USDA NRCS cover crop guidance; Iowa State University Extension
agronomy guides; USDA NASS for multi-year average yields; GRDC (Australia)
pulse agronomy grow notes for the two pulses (lentil, chickpea), whose
nitrogen-credit figures are explicitly flagged as order-of-magnitude since
published trials disagree.

## 3. Reference evapotranspiration, ET0 (`evapotranspiration.py`)

Full FAO-56 Penman-Monteith, computed daily, not a simplified Hargreaves or
Thornthwaite shortcut:

```
ET0 = [0.408 · Δ · (Rn − G) + γ · (900 / (T + 273)) · u2 · (es − ea)]
      ─────────────────────────────────────────────────────────────
                      Δ + γ · (1 + 0.34 · u2)
```

where, matching the code's variable names to FAO-56's equation numbers:

- `Δ` – slope of the saturation vapour pressure curve (eq. 13), from mean
  temperature.
- `γ` – psychrometric constant (eq. 8), from atmospheric pressure, itself
  estimated from a fixed elevation assumption of 300 m (eq. 7). This is the
  one input not fetched live; a per-site elevation lookup is listed as a
  future improvement.
- `Rn` – net radiation (eq. 38–40): net shortwave `Rns = (1 − α) · Rs` with
  albedo `α = 0.23`, minus net longwave `Rnl`, which uses the
  Stefan-Boltzmann relation, both day's max/min temperature in Kelvin, the
  actual vapour pressure, and the ratio of measured to clear-sky radiation
  (`Rs/Rso`, clipped at 1).
- `Ra`, `Rso` – extraterrestrial and clear-sky radiation (eq. 21–28), from
  the site's latitude and day-of-year (solar declination, sunset hour
  angle, inverse relative Earth-Sun distance).
- `es`, `ea` – saturation and actual vapour pressure (eq. 11, 12, 17–19),
  from max/min temperature and mean relative humidity.
- `G` – soil heat flux density, set to 0 (eq. 42: negligible at a daily
  time step).
- `u2` – wind speed at 2 m, taken directly from POWER's `WS2M`.

Reference: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop
evapotranspiration — Guidelines for computing crop water requirements.*
FAO Irrigation and Drainage Paper 56, Chapter 4.

## 4. Crop water demand, ETc (`crop_water_demand_mm`)

A single Kc (crop coefficient) curve is built per crop from three
published points (`kc_ini`, `kc_mid`, `kc_end`) split 20% / 40% / 40% into
initial, development-plus-mid, and late-season stages:

```
Kc(day) = kc_ini                                  for day in [0, 0.2·L)
        = linear(kc_ini → kc_mid)                 for day in [0.2·L, 0.6·L)
        = linear(kc_mid → kc_end)                 for day in [0.6·L, L)
```

where `L` is `season_length_days`. This 20/40/40 split is a documented
FAO-56 simplification for crops whose exact stage lengths are not
published for the target region, not an invented shortcut.

Seasonal water demand is then:

```
ETc = Σ  ET0(day) · Kc(day),   for day = 0 .. L−1
```

aligned against the first `L` days of the fetched weather window for that
crop.

## 5. Climate suitability filter (`climate_suitability.py`)

Rather than assuming a crop's growing season starts on the request's
`start_date` (an earlier version did this, and it wrongly excluded maize
from Iowa, because a 1 January start lands mid-winter), the filter slides
a window of length `season_length_days` across the *entire* fetched period
and finds whichever window's mean temperature is closest to the crop's
`(min_temp_c + max_temp_c) / 2` midpoint. That is the best-case planting
window the data offers. A crop passes if that window's mean temperature
falls within `[min_temp_c, max_temp_c]`.

This is a necessary filter, not a cosmetic one: without it, the engine
could rank a rotation using a crop that cannot actually grow at the
queried site and look globally capable without ever checking. It needs at
least a season's worth of data to find a viable window, which is why the
demo fetches close to a full year by default regardless of hemisphere.

A related function, `frost_days_in_best_window`, counts days with
`T2M_MIN` below 0 °C within that same best-fit window, as a cheap real-data
frost signal (not a predicted frost date).

`climate_mismatched_crops` applies the same check to a farmer's *stated*
current rotation, which (unlike recommended candidates) never passes
through the filter above, since it is what they are already doing, not a
suggestion. Without this check, an unsuitable self-reported crop would
silently be scored as if it could grow.

## 6. Candidate generation and the agronomic hard filter

`generate_candidate_sequences` takes the Cartesian product of the
climate-suitable crop pool to the sequence length (3, by default):
`|crops| ^ sequence_length` raw sequences. Each is passed through
`passes_agronomic_rules`, a hard constraint, not a soft penalty: a crop
family may not repeat within `min_family_gap_years` (2, by default). A
sequence either satisfies this or is discarded outright.

This hard-filter-then-score structure, rather than folding the rule into a
penalty term, was a deliberate simplification over an earlier sigmoid-plus-
penalty design: it is easier to test (a sequence is either legal or it is
not) and easier to explain to a judge live.

**Scaling note**: because this is a full Cartesian product, candidate
generation is `O(n^k)` in the crop pool size `n` and sequence length `k`.
At 10 crops and a 3-year sequence this is a few hundred candidates, trivial
to score exhaustively. It would need a smarter search (e.g. branch and
bound, or simply capping the pool before the product) before extending to
a much longer rotation or a substantially larger crop catalogue.

## 7. Per-year scoring

For each crop in a candidate sequence, four scores are computed in `[0, 1]`
against the previous crop in the sequence and the site's
`EnvironmentalBaseline` (seasonal rainfall, root-zone wetness, soil organic
carbon).

### 7.1 Soil score

```
soil = 0.35 · n_component + 0.25 · carbon_component
     + 0.15 · root_bonus   + 0.25 · erosion_component
```

- `n_component = tanh(max(nitrogen_balance_kg_ha, 0) / 100)` — only
  nitrogen *additions* count toward soil score; a nitrogen-depleting crop
  contributes 0 here (its debit is instead captured in the impact metrics
  against the baseline, §9). The `tanh` keeps the component bounded as
  nitrogen credit grows.
- `carbon_component = clip(1 − soc / soil_degradation_baseline, 0, 1)`,
  i.e. more *headroom* below a reference depleted-soil carbon level (15
  g/kg by default) scores higher. If SoilGrids returned no reading for
  this point, `carbon_component` is fixed at 0.5 (neutral) rather than
  being computed from a fallback number that would otherwise silently
  score every missing-data site as maximally degraded — a bug found and
  fixed during this project's own testing, now covered by a regression
  test.
- `root_bonus = 0.2` if this crop's `root_depth_class` differs from the
  previous crop's, else 0, reflecting that alternating rooting depths
  helps break up compaction and exploit a different soil-moisture layer.
- `erosion_component`, see §10.

The sub-weights (0.35 / 0.25 / 0.15 / 0.25) are this project's own
construction: agronomically motivated, but not drawn from a single
published "rotation suitability index" formula, because no such formula in
a directly usable form appears to exist in the literature. Treat the soil
score's *ranking* as more trustworthy than its *absolute value*.

### 7.2 Water score

```
available = seasonal_precip_mm · (0.5 + 0.5 · mean_root_zone_wetness)
deficit   = max(ETc − available, 0)
water     = 1 − deficit / max(ETc, 1)
```

`available` blends rainfall with how wet the root zone already is
(`GWETROOT`, a 0–1 saturation fraction): a crop's water demand is treated
as easier to meet when stored soil moisture is already high, not just when
this season's rainfall alone covers it.

### 7.3 Resilience score

A direct lookup on the crop's published drought tolerance:
`{"low": 0.2, "medium": 0.6, "high": 1.0}`, defaulting to 0.5 for an
unrecognised value.

### 7.4 Revenue score

```
revenue = 0                              if has_market_revenue is false
        = tanh(typical_yield_t_ha / 8)   otherwise
```

Deliberately yield-only, with no commodity price multiplied in. Prices are
volatile month to month, and even USDA's own same-year figures were found
to be inconsistent across reports when checked during this project, so a
fixed $/unit here would be a precision claim the project cannot responsibly
back up. `tanh(yield / 8)` maps the current crop set's yield range
(2.4–11 t/ha) into `[0, 1]` without needing a price at all.

### 7.5 Combining the four scores

```
weights = normalize(soil_w, water_w, resilience_w, revenue_w)   // sum to 1
year_score = weights.soil · soil + weights.water · water
           + weights.resilience · resilience + weights.revenue · revenue

RSI = Σ  (0.9 ^ year_index) · year_score[year_index]
```

Weights come from the farmer's stated priorities and are always
re-normalised to sum to 1 regardless of what raw values are supplied. The
0.9 per-year discount weights near-term impact more heavily than later
years in the sequence, on the basis that soil and water conditions this
year are more certain than a forecast three years out.

## 8. Explanation layer (`explain_year`)

The four `[0, 1]` scores above are not meaningful to a farmer on their own,
so `explain_year` re-derives the same underlying real-unit numbers
(kilograms of nitrogen, millimetres of water deficit, qualitative erosion
and revenue levels, bare-field days) and assembles them into plain-language
sentences. It deliberately does not claim a running soil nitrogen *stock*;
the engine does not model a cumulative soil nitrogen pool across years, only
each crop's own net balance for that year.

## 9. Impact metrics against a baseline (`compute_impact_metrics`)

Every ranked rotation is also compared, in real units, against a
continuous monoculture baseline (`maize`, the most commonly practised
rotation in the demo region today, set in `crops.json`'s `_baseline_crop`):

```
nitrogen_fertilizer_avoided_kg_ha = Σ rotation_N  −  baseline_N · length
water_saved_mm                    = baseline_ETc · length  −  Σ rotation_ETc
bare_field_days_avoided           = baseline_bare_days · length  −  Σ rotation_bare_days
```

Each is signed so a positive number always means "better than the
baseline"; a rotation that uses *more* water than continuous maize (a
real, disclosed possibility for some high-value perennial rotations) shows
a negative `water_saved_mm` rather than hiding the trade-off.

These three numbers are then mapped to UN Sustainable Development Goal
tags, attached only when the rotation actually improves on that specific
metric, not asserted unconditionally:

| Condition | Tag |
|---|---|
| `water_saved_mm > 0` | SDG 6, Clean Water and Sanitation |
| `nitrogen_fertilizer_avoided_kg_ha > 0` | SDG 13 (Climate Action) and SDG 15 (Life on Land) |
| `bare_field_days_avoided > 0` and no SDG 15 tag yet | SDG 15 (Life on Land) |

## 10. Erosion protection heuristic (`erosion_protection_score`)

```
erosion = clip(by_role[role] + (0.1 if root_type starts with "fibrous"), 0, 1)

by_role = {
  perennial_forage_legume: 1.0,
  cover_crop:              0.9,
  cash_grain:              0.5,
  cash_grain_legume:       0.3,
}
```

This is explicitly a qualitative indicator from crop role and root habit,
not a RUSLE (Revised Universal Soil Loss Equation) C-factor. A proper
C-factor needs site-level slope and tillage-practice modelling (NRCS
RUSLE2 Handbook), and even NRCS's own management files are inconsistent on
this point (Chesapeake Bay Program Scientific and Technical Advisory
Committee review, 2017). The ranking encodes a well-documented general
pattern instead: continuous perennial cover and dedicated cover crops
protect soil far better than annual row crops with a bare-soil
establishment period, and legume row crops such as soybean leave less
persistent residue than grain crops (a widely reported comparison, e.g.
Iowa State University Extension).

## 11. Bare-field days (`bare_field_days_in_year`)

```
bare_field_days = max(0, 365 − season_length_days)
```

A deliberately simple proxy for how long a field typically sits without
living cover each year, directly answering the brief's prompt that a tool
like this "may highlight times when fields are typically bare." It is
entirely this project's own construction: the *motivation* is literature-
backed (bare soil between crops is a well-documented erosion and
nutrient-leaching risk window, the whole reason cover crops exist as a
practice), but the number itself is a rough estimate from typical season
length, not an actual farm planting calendar. It does not credit
post-harvest residue, which still offers some protection after the
"season" technically ends, and it does not know whether a different crop
(for example a cover crop slotted into the same rotation year) fills that
gap in practice. Perennials (`season_length_days = 365`, e.g. alfalfa)
score 0 by construction, which is accurate: once established, they hold
the field year-round.

## 12. Standing caveats (`generate_risks_and_gaps`)

Four caveats are attached to every rotation this engine produces,
regardless of which crops are involved, because they apply to the method
itself rather than to any one candidate:

1. Climate suitability is checked on temperature only. Day length, frost
   timing, rainfall seasonality and local pest or disease pressure are not
   modelled.
2. Revenue potential is a relative, yield-based proxy, not a profit
   calculation. Commodity price, input costs and labour are excluded.
3. Erosion protection is the qualitative indicator from §10, not a
   site-specific soil-loss model.
4. Bare-field days are the proxy from §11, not an actual planting
   calendar.

On top of these, rotation-specific flags are appended when they apply:
a frost warning (from §5), a note when SoilGrids had no reading at this
exact point, a note when a perennial forage crop appears for only one year
in a sequence (real perennial forage is established once and kept in the
ground for several years, not replanted annually, and this engine does not
model establishment-year yield drag), the climate-mismatch note from §5
for a farmer's self-reported current rotation, and a note for any crop
flagged `flood_irrigated: true` in `crops.json` (currently only rice):
the Kc × ET0 water-demand calculation covers crop transpiration only, not
a flooded paddy's standing-water maintenance or percolation losses, so its
real water use is likely well above what this engine's water score and
impact metrics report.

## 13. Known limitations not yet addressed

- **Global coverage is uneven between the two data sources.** Tested live
  against eight sites worldwide (Iowa, Lagos, Mumbai, Cairo, Punjab,
  Nairobi, Reykjavik, São Paulo): NASA POWER returned usable weather data
  everywhere, and the climate-suitability filter behaved correctly (it
  dropped maize, soybean and alfalfa for Reykjavik on temperature grounds,
  kept all eight crops elsewhere). SoilGrids did not: only the Iowa site
  returned real values for clay, sand, pH and organic carbon at the time of
  testing, every other site returned a valid `200` response with every
  property `null`. The `soil_carbon_is_estimated` fallback (§7.1) means
  this degrades gracefully to a neutral score rather than a wrong one, but
  soil-score precision should be assumed "generic estimate" almost
  anywhere outside a handful of well-covered points, not treated as site-
  specific. See §15 for a worked look at options to close this.
- **The crop dataset was temperate-US-centric, independent of the weather
  data's own global reach.** At the time of this test (eight crops: maize,
  soybean, wheat, oats, rye, alfalfa, lentil, chickpea), all eight passed
  the temperature filter at every site except Reykjavik, which sounds
  global, but passing a temperature check is not the same as being
  agronomically or culturally appropriate: a farmer in Lagos or Mumbai
  would have gotten rotation advice built entirely from that list, not
  rice, sorghum, millet or cassava. Rice and sorghum were subsequently
  added (§15) specifically to test whether the dataset could generalise;
  it could, cleanly, with the same sourcing rigour as the rest of
  `crops.json`. That is evidence the approach scales, not evidence the
  gap is closed — millet, cassava and most other staples a Lagos or Mumbai
  farmer would actually plant are still missing, and this remains a
  dataset-scope gap, not a bug in the filter.
- **SoilGrids clay, sand and pH are fetched but unused.** Only organic
  carbon currently feeds a score.
- **No cumulative soil nitrogen or carbon pool across years.** Each year's
  nitrogen balance is independent; a rotation's long-run soil trajectory is
  not simulated.
- **No polygon input.** The engine takes a single lat/lon point; NASA
  POWER's own resolution (~55 km per cell) means a precise farm boundary
  would not currently improve accuracy, so a polygon is treated as a
  frontend concern that reduces to a centroid before calling the API.
- **Combinatorial candidate generation**, as noted in §6, does not scale
  past a modest crop pool and sequence length without a smarter search.
- **GWETROOT/GWETTOP are a SMAP stand-in, not SMAP itself.** Both are
  reanalysis-model outputs (MERRA-2/GEOS-calibrated), not a direct
  satellite soil-moisture reading, and are documented as such in
  `data-science-approach.md`.

## 14. References

- Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop
  evapotranspiration — Guidelines for computing crop water requirements.*
  FAO Irrigation and Drainage Paper 56.
- Herridge, D.F., Peoples, M.B., Boddey, R.M. (2008). Global inputs of
  biological nitrogen fixation in agricultural systems. *Plant and Soil*,
  311, 1–18.
- GRDC (Grains Research and Development Corporation, Australia). Pulse
  agronomy grow notes (lentil, chickpea).
- USDA NASS. Multi-year average crop yield statistics.
- USDA NRCS. Cover crop guides.
- Iowa State University Extension. Agronomy guidance for Central Iowa row
  crops.
- NRCS RUSLE2 Handbook; Chesapeake Bay Program Scientific and Technical
  Advisory Committee (2017) review of RUSLE2 management-file consistency.
- NASA POWER Daily API documentation:
  https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- ISRIC SoilGrids v2.0 FAQ:
  https://www.isric.org/explore/soilgrids/faq-soilgrids

## 15. Options considered for the global-coverage gap (§13)

Ranked by effort against how much they'd actually move the two gaps
above. Status notes record what was actually done, not just proposed.

### Soil data reliability

1. **Retry a few times on a null response before accepting it** (low
   effort). **Done** — `fetch_soilgrids` now retries up to twice (1.5s
   apart) when `soc` comes back null. Tested live: it did not recover
   Lagos or Paris (both still null after retrying, so whatever is
   happening there is not a one-off transient blip on that timescale),
   but it costs nothing on the success path (confirmed: the already-
   working Ames point still returns in ~1.3s, no retry triggered) and may
   still help some other, genuinely transient miss.
2. **Replace the flat neutral (0.5) fallback with a climate-informed
   default.** **Explored, not implemented.** The idea was to use the
   site's own POWER data (mean temperature, precipitation) to pick a
   better "best guess" than one constant everywhere. Looked for a
   defensible source of typical topsoil organic carbon in g/kg by broad
   climate class and didn't find one precise enough to cite responsibly
   — the literature reports carbon *stocks* per unit area, which need a
   bulk-density assumption to convert to a concentration, and that
   conversion would have added invented precision on top of an already
   rough idea. Dropped rather than ship a number this project can't back
   up; the existing flat, clearly-flagged-as-estimated fallback stays.
3. **Switch from SoilGrids' REST point-query endpoint to its WCS raster
   tiles and sample the pixel directly** (high effort, not built). ISRIC's
   own docs suggest the raster service is the more authoritative path;
   the REST query endpoint we currently call may simply be less reliable.
   This needs a raster library (e.g. `rasterio`) and tile-index math, real
   engineering, not a config change, and is the right long-term fix if
   this project continues past the hackathon.
4. **Add a second global soil source as a fallback** (high effort, not
   built, and a new source to vet and cite with the same rigour as
   everything else in `data/crops.json`). Not recommended for this
   weekend.

### Crop dataset regional narrowness

1. **Add a handful of crops for other major climate zones**, sourced the
   same way lentil and chickpea were (FAO-56 Table 12 for Kc, a credible
   regional source for nitrogen balance and yield, every disagreement
   between sources flagged in `source`). **Done** — rice (flooded,
   tropical/monsoon) and sorghum (semi-arid) were added; both pass the
   climate filter at every tested global site except Reykjavik,
   demonstrating the dataset generalises past the US Midwest without
   claiming full global completeness. Adding rice also surfaced a real
   modelling gap worth having found: the Kc × ET0 water-demand calculation
   only covers transpiration, not a flooded paddy's standing-water and
   percolation losses, so rice now carries its own dedicated caveat in
   `risks_and_gaps` (see §12) rather than silently under-reporting its
   real water use.
2. **Tag crops by region/biome and filter on that in addition to
   temperature** (medium effort). Temperature alone already lets through
   crops that pass the number but would be a strange recommendation for
   that place; an explicit region tag plus a "shown for a reason other
   than pure climate match" note would be more honest than silence.
3. **Adopt FAO EcoCrop/GAEZ v4 wholesale** (high effort). Already assessed
   in `data-science-approach.md` as not worth a raster-extraction
   pipeline for a handful of crops; that conclusion still holds even with
   more crops in view, unless the project moves well past hackathon scope.

2 and 3 remain open; neither was needed to demonstrate the dataset
generalises, which was the actual goal here, not "now covers the world."
That stronger claim would not survive a judge who checks it, and this
project's whole approach has been to never make one it can't back up.

