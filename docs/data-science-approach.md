# Data science approach — status and open questions

Covers what's built, why it's built this way, what it deliberately leaves
out, and where I'd like a second opinion before we split up further work.

## The core idea

Given a farm location, recommend which 3-year crop rotation best balances
soil health, water sustainability, and drought resilience, using live NASA
Earth observation data rather than static lookup tables. Output a ranked
list of rotations with a score breakdown the frontend can turn into
"why this rotation" visuals.

Demo location: Central Iowa (Ames, 42.0308, -93.6319) — chosen over
Punjab/Spain for richest public validation data (USDA yield history) if we
want to sanity-check outputs later.

## How a request flows through the system

```
lat/lon + priority weights
  -> NASA POWER API: daily rainfall, temp, humidity, wind, solar radiation,
     root-zone/surface soil wetness (GWETROOT/GWETTOP)
  -> SoilGrids API: topsoil clay/sand %, pH, organic carbon
  -> FAO-56 Penman-Monteith: daily reference ET0 from the POWER weather data
  -> per candidate rotation: crop water demand (Kc x ET0) for each crop
  -> weighted scoring: soil score + water score + resilience score per year
  -> ranked list of rotations, highest score first
```

Both API clients cache responses locally (`data/cache/`) so repeated runs
don't keep re-hitting the APIs during development or the demo itself.

## Why no SMAP / NDVI / Earth Engine yet

The original idea list included SMAP soil moisture and MODIS/Landsat NDVI,
both of which need Google Earth Engine. That's a significant setup cost
(auth, raster processing) for a weekend build. Instead I'm using NASA
POWER's `GWETROOT`/`GWETTOP` (root-zone and surface soil wetness) as the
soil-moisture signal — same API call as everything else, no extra auth.
SMAP/NDVI are still good stretch goals if we have time left after the core
tool works end to end.

**Satellite vs. ground-based measurement, and why this matters here**:
every input this engine uses (NASA POWER, SoilGrids) is itself a *modelled*
estimate, not a direct field reading — POWER's weather variables come from
reanalysis models (MERRA-2/GEOS) calibrated against a mix of satellite and
ground-station observations, and SoilGrids is a machine-learning prediction
from sparse global soil survey points, not a sample taken from this
specific field. That's exactly why every rotation's `risks_and_gaps`
recommends a local soil test and an agronomist's confirmation before
adopting it: this tool narrows down *plausible* options using
Earth-observation-scale data, a real soil sample and a farmer's lived
experience of their own field are a finer-grained source of truth than
any satellite-derived product, including the ones (SMAP, NDVI) this
project didn't get to.

**On pest and disease cycles**: the brief calls out "opportunities for
rotations that could interrupt pest cycles" as something a tool like this
might highlight. This project doesn't model pest/disease pressure directly
(no pest incidence data source was in scope), but the hard agronomic rule
that rejects repeating a crop family within a 2-year gap
(`passes_agronomic_rules`) exists specifically because continuous
same-family planting is what lets family-specific soil pests and diseases
(e.g. soybean cyst nematode, corn rootworm) build up — so every candidate
rotation this engine proposes already satisfies that goal by
construction, even though it isn't scored or surfaced as its own metric.

## Why the scoring math is simpler than the original plan

The original sketch had a sigmoid-based RSI formula with an exponential
time-discount and an agronomic penalty function. I simplified it to:

1. **Hard filter first**: reject any candidate sequence that repeats a crop
   family within a configurable gap (default: no same family within 2
   years). This is a real constraint, not a soft penalty — a sequence
   either passes or doesn't.
2. **Normalize each remaining criterion to 0-1** (soil, water, resilience)
   per year, rather than letting them grow unbounded.
3. **Weighted sum** using the farmer's priority sliders, with a 0.9
   per-year discount so near-term impact counts more than year 3.

Same underlying agronomy, easier to explain live and to unit test. Detail
on what's literature-backed vs. my own construction:

- **FAO-56 Penman-Monteith ET0 and the Kc crop-coefficient approach** are
  exact, from Allen et al. (1998), FAO Irrigation and Drainage Paper 56 —
  this is the global standard, not something I approximated.
- **The suitability scoring formulas** (the soil/water/resilience 0-1
  scores, the specific sub-weights) are my own construction, agronomically
  motivated but not pulled from a single published "rotation suitability
  index" paper — I don't think one exists in a form we could just adopt.
  Worth treating as a v1 to refine, possibly against NRCS's soil health
  assessment framework if we want more authority behind it.
- **Nitrogen balance direction** (legumes positive, heavy feeders like
  maize negative) reflects real biological nitrogen fixation research
  (Herridge et al. 2008, *Plant and Soil*), though the specific per-crop
  numbers in `crops.json` came from USDA/Iowa State extension guidance, not
  that paper directly.
- **Bare-field days** (`bare_field_days_in_year`, `impact_metrics.bare_field_days_avoided`)
  is entirely my own construction: `365 - season_length_days`, a proxy for
  how long a field sits without living cover each year. The *motivation*
  is real and literature-backed (bare soil between crops is a well-known
  erosion and nutrient-leaching risk window — this is the whole reason
  cover crops exist as a practice), but the specific number is a rough
  estimate from typical season length, not an actual farm planting
  calendar, and doesn't credit post-harvest residue. Flagged as such in
  every response's `risks_and_gaps`.

## The crop dataset (`data/crops.json`)

Ten crops: maize, soybean, winter wheat, oats, cereal rye (cover crop),
alfalfa, lentil, chickpea, rice, sorghum. Each has nitrogen balance, water
requirement (Kc curve + season length), temperature tolerance, root depth
class, drought tolerance, and a cited source. The first six are Central
Iowa rotation staples; lentil and chickpea were added as additional legume
break-crop options (not Iowa-typical, but agronomically valid) to widen the
candidate pool and give the frontend's crop-card set something to match
against; rice and sorghum were added afterwards specifically to test
whether the dataset could extend beyond a US-Midwest-temperate crop list —
see `docs/algorithm.md` sections 13 and 15 for what that test found.

There's no single clean global API with all of these fields together.
Closest real sources if we expand the crop list or add other regions:
- **FAO-56 Tables 12/22** — Kc values and rooting depth, ~80 crops, PDF
  tables (what the current 10 were transcribed from).
- **FAO EcoCrop**, now folded into **GAEZ v4** (gaez.fao.org) — temperature/
  rainfall/pH tolerance for 2,500+ species, but distributed as GIS raster
  data, not a simple per-crop lookup; would need extraction code.
- **Herridge et al. 2008** — nitrogen fixation rates by legume type.
- **GRDC (Australia) pulse grow notes** — used for lentil/chickpea nitrogen
  credit and climate tolerance, since those two aren't covered as well by
  the US-focused sources above; published credit figures disagree between
  studies, so those two values are flagged in `crops.json` as rough
  order-of-magnitude estimates, not settled numbers.

Recommendation: keep hand-curating against these named sources (systematic,
traceable) rather than trying to build a raster-extraction pipeline against
GAEZ for a handful of crops — not worth the time unless we need a much
larger crop list.

Note: soil pH is not a tracked field in this engine. If the frontend (crop
"cards") displays a pH value per crop, that number comes from the frontend
team's own research, not from `crops.json`.

**Card-to-engine mapping**: the frontend's TCG-style crop cards cover more
crops than the engine does. Only these 8 cards correspond to a real
`crops.json` entry and can actually be recommended: wheat (`winter_wheat`),
rye (`cereal_rye_cover`), oats, maize, lentils, chickpea, soybean, alfalfa
(no card yet as of this note -- worth prioritizing). The other 8 cards
(rice, sunflower, cotton, rapeseed, beetroot, carrots, potatoes, coffee,
tea) are drawn but have no backing data, so the engine will never
recommend them -- fine as unused art for the demo, but worth knowing if a
judge asks why a given card never shows up in a result.

## What's deliberately not built yet

- **No profit/yield dimension.** The scoring only covers soil health,
  water, and resilience — it structurally can't produce a "Maximum Profit"
  style recommendation from the original plan's output table, because nothing
  currently represents yield or price. Would need per-crop yield data
  (USDA NASS has Iowa county history) and commodity prices.
- **No polygon/boundary input** — takes a single lat/lon point. NASA POWER's
  resolution is ~55km per grid cell, so a precise farm boundary wouldn't
  currently improve accuracy; a polygon is a reasonable frontend UX layer
  that reduces to a centroid point before calling the API.
- **Date range defaults to calendar year 2023** but is now a request
  parameter, not hardcoded.
- **No automated tests yet** for the engine (ET0 calculation, scoring).

## What's working right now

- `backend/app/data/`: NASA POWER and SoilGrids clients, both verified
  against live data, both caching locally.
- `backend/app/engine/`: FAO-56 ET0, crop water demand, rotation scoring,
  candidate generation with the hard agronomic filter.
- `backend/app/main.py`: a FastAPI endpoint (`POST /rotations`) wrapping all
  of the above, verified with a live request/response.
- `backend/scripts/demo.py`: same pipeline as a standalone CLI script, no
  server needed, good for quick iteration.
- `docs/api-contract.md`: the request/response shape, so the frontend can
  start building against a spec immediately.

## Questions for this meeting

1. Does the soil/water/resilience weighting feel right, or should we adjust
   the sub-weights inside `soil_score`/`water_score` before we start
   tuning against a real narrative (e.g. "profit vs. regeneration")?
2. Do we prioritize the profit/yield dimension next, or expanding the crop
   list to support a second location for comparison?
3. Who owns adding tests vs. who owns the profit dimension vs. who owns
   crop data expansion — splitting this three ways seems reasonable given
   where we are.
