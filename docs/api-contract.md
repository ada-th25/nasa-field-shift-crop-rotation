# API contract: `POST /rotations`

This is the one endpoint the frontend needs for v1. It's a stateless FastAPI
service, CORS-open, returns plain JSON. Base URL during development:
`http://localhost:8000` (run with `uvicorn app.main:app --reload` from `backend/`).

## `GET /health`

Returns `{"status": "ok"}`. Use for a connectivity check.

## `POST /rotations`

### Request body

```json
{
  "lat": 42.0308,
  "lon": -93.6319,
  "start_date": "20230101",
  "end_date": "20231231",
  "priority_weights": { "soil": 0.3, "water": 0.3, "resilience": 0.15, "revenue": 0.25 },
  "sequence_length": 3,
  "top_n": 5,
  "current_rotation": ["maize"]
}
```

All fields are optional except `lat`/`lon` — the rest have defaults shown above.

| Field | Type | Notes |
|---|---|---|
| `lat`, `lon` | float | Decimal degrees. A single point (farm centroid), not a polygon — see note below. |
| `start_date`, `end_date` | string `YYYYMMDD` | Weather window pulled from NASA POWER. Defaults to calendar year 2023. |
| `priority_weights` | object | Keys `soil`, `water`, `resilience`, `revenue` (farmer priority sliders). Don't need to sum to 1, they're normalized server-side. Any key you omit falls back to its default weight rather than zero — so a client sending only `{"soil": 1}` still gets some water/resilience/revenue influence, not a pure soil-only ranking. `revenue` is new: it's a relative yield-based proxy, not a real profit figure (see `explanation.revenue_potential` below). |
| `sequence_length` | int | How many years in a candidate rotation. 3 is the current default and what's been tested; larger values are untested and the candidate count grows combinatorially. |
| `top_n` | int | How many ranked rotations to return. |
| `current_rotation` | array of strings or omitted | The farmer's actual current rotation, crop names from `data/crops.json` (e.g. `["maize"]` for continuous maize, or a multi-year list). Not filtered by the climate check — it's what they're already doing, not a recommendation. Scored through the identical pipeline and returned as `current_rotation` in the response, so the UI can show it side by side with `top_rotations` rather than only inferring it from `impact_metrics`. An unrecognized crop name returns HTTP 400. |

**On the point vs. polygon question**: NASA POWER's weather data is ~55km grid resolution, so a precise field boundary doesn't currently improve accuracy — if the frontend lets users draw a farm boundary (good UX), reduce it to a centroid point client-side before calling this endpoint. No backend change needed for that.

### Response body

```json
{
  "soil": {
    "clay_pct": 31.4,
    "sand_pct": 14.8,
    "ph": 6.6,
    "soc_g_kg": 49.0
  },
  "mean_et0_mm_day": 3.06,
  "top_rotations": [
    {
      "sequence": ["alfalfa", "maize", "alfalfa"],
      "rsi": 1.809,
      "year_breakdown": [
        {
          "crop": "maize",
          "soil_score": 0.3,
          "water_score": 1.0,
          "resilience_score": 0.2,
          "revenue_score": 0.88,
          "year_score": 0.64,
          "explanation": {
            "nitrogen_balance_kg_ha": -150,
            "water_demand_mm": 285.5,
            "water_deficit_mm": 0,
            "root_diversified_from_previous": true,
            "drought_tolerance": "low",
            "erosion_protection": "medium",
            "revenue_potential": "high",
            "summary": "Draws down an estimated 150 kg N/ha of soil nitrogen; will need fertilizer input. Water demand (~286 mm) is comfortably covered by expected rainfall and stored soil moisture. Different rooting depth than the previous crop, helping break up compaction and access a different soil moisture layer. Low drought tolerance. Medium erosion protection from ground cover and residue. High relative revenue potential based on typical yield."
          }
        }
      ],
      "impact_metrics": {
        "baseline": "continuous maize",
        "nitrogen_fertilizer_avoided_kg_ha": 600,
        "water_saved_mm": -1164.5,
        "water_saved_pct": -136.0,
        "sdg_tags": [
          {
            "sdg": "SDG 13",
            "label": "Climate Action",
            "rationale": "Avoids ~600 kg/ha of synthetic nitrogen vs. continuous maize, reducing fertilizer-linked emissions."
          }
        ]
      },
      "risks_and_gaps": [
        "Climate suitability is checked on temperature only -- day length, frost timing, rainfall seasonality, and local pest or disease pressure aren't modelled. Have an agronomist confirm this rotation suits local conditions before adopting it.",
        "Revenue potential is a relative, yield-based proxy, not a real profit calculation -- it excludes commodity price, input costs, and labour, all of which vary too much by region and season to responsibly estimate here.",
        "Erosion protection is a qualitative indicator based on crop role and root habit, not a site-specific soil-loss model (e.g. RUSLE2) -- slope, tillage practice, and residue management all affect real erosion risk and aren't accounted for here.",
        "alfalfa: the best available growing window in the fetched weather data still included sub-zero days. Check local frost dates before planting.",
        "alfalfa is shown here for a single year, but in practice a perennial forage crop like this is established once and kept in the ground for several years, not replanted annually -- this rotation doesn't model establishment cost or yield drag from doing that."
      ]
    }
  ],
  "current_rotation": {
    "sequence": ["maize"],
    "rsi": 0.595,
    "year_breakdown": [ "...same shape as top_rotations[].year_breakdown..." ],
    "impact_metrics": { "baseline": "continuous maize", "nitrogen_fertilizer_avoided_kg_ha": 0, "water_saved_mm": 0.0, "water_saved_pct": 0.0, "sdg_tags": [] },
    "risks_and_gaps": [ "...the standing always-on gaps, no rotation-specific ones since it's a single-crop monoculture..." ]
  }
}
```

Note: this is the engine's actual current top pick for the Iowa demo site (live output, captured above). Adding `revenue_score` brought maize back into the top rotation — previously (before revenue scoring existed) it was excluded from every top-5 result, which `docs/validation.md` flagged as the model's main divergence from real Iowa practice. The alfalfa-as-annual artifact from the erosion-scoring change is still present (see the `single_year_perennial` caveat above and `docs/validation.md`).

| Field | Type | Notes |
|---|---|---|
| `soil.clay_pct`, `soil.sand_pct` | float, % | Topsoil (0-5cm) texture, from SoilGrids. **Can be `null`** — SoilGrids has gaps at some real-world points (e.g. high-latitude/coastal sites); handle null in the UI rather than assuming a number. |
| `soil.ph` | float or null | Topsoil pH. Same null caveat as above. |
| `soil.soc_g_kg` | float or null | Soil organic carbon, g/kg. Same null caveat as above. |
| `mean_et0_mm_day` | float | Average daily reference evapotranspiration over the requested date window. Informational — a high-level water-demand signal for the UI. |
| `top_rotations` | array | Ranked highest RSI first. |
| `top_rotations[].sequence` | array of strings | Crop names in year order, matching keys in `data/crops.json`. |
| `top_rotations[].rsi` | float | Rotational Suitability Index — the overall ranking score. Not bounded to a fixed range (it's a discounted sum across years), higher is better, only meaningful relative to other rotations in the same response. |
| `top_rotations[].year_breakdown` | array | One entry per year of the sequence: `soil_score`, `water_score`, `resilience_score`, `revenue_score` (each 0-1) plus that year's combined `year_score`. Useful if the UI wants to show *why* a rotation ranked well (e.g. a bar chart per year). |
| `year_breakdown[].explanation` | object | The 0-1 scores translated into real units and plain language, for showing a farmer *why* — not just "soil_score: 0.39" but "adds ~40 kg N/ha". Fields: `nitrogen_balance_kg_ha` (this crop's own net N for the year, not a cumulative soil N stock — we don't model that), `water_demand_mm`, `water_deficit_mm` (0 if demand is covered by expected rainfall/soil moisture), `root_diversified_from_previous` (bool), `drought_tolerance`, `erosion_protection` (`"low"`/`"medium"`/`"high"`, see below), `revenue_potential` (`"none"`/`"low"`/`"medium"`/`"high"`, see below), and `summary` (a ready-to-display sentence, or build your own from the fields). |
| `explanation.erosion_protection` | string | Qualitative, not a RUSLE soil-loss calculation — derived from the crop's role and root habit (continuous cover crops and perennial forage score highest, row-crop legumes like soybean lowest, matching well-documented general erosion patterns). Treat as a relative signal ("this crop protects soil better than that one"), not a measured erosion rate. |
| `explanation.revenue_potential` | string | `"none"` for crops with no market revenue (e.g. a cover crop terminated before harvest), otherwise a relative tier from `typical_yield_t_ha` (`data/crops.json`) — a stable multi-year-average order of magnitude, deliberately not combined with a commodity price (see `revenue_score` note in `risks_and_gaps`). Treat as "roughly how much this crop is worth bringing to market relative to the others here," not a dollar figure. |
| `top_rotations[].impact_metrics` | object | This rotation vs. a continuous-monoculture baseline (currently `data/crops.json`'s `_baseline_crop`, "maize"), in real units rather than abstract scores. |
| `impact_metrics.water_saved_mm`, `.water_saved_pct` | float | Water demand avoided vs. the baseline over the full sequence. Can be negative (the rotation uses *more* water than the baseline, e.g. a sequence including alfalfa) — don't clamp this to zero in the UI, a negative value is a real and useful signal. |
| `impact_metrics.nitrogen_fertilizer_avoided_kg_ha` | float | Net synthetic nitrogen avoided vs. the baseline, summed over the sequence. Can also be negative. |
| `impact_metrics.sdg_tags` | array | Zero or more of `{sdg, label, rationale}`, only included when the rotation actually improves on the baseline for that metric — this list can be empty for a rotation that doesn't outperform the baseline on any tracked metric. Don't assume every rotation has at least one tag. |
| `top_rotations[].risks_and_gaps` | array of strings | Plain-language caveats for this specific rotation — what the challenge brief calls "information gaps" and "risks that would need local review." Always includes three general caveats (climate check is temperature-only; revenue potential is a yield-based proxy, not real profit; erosion protection is qualitative, not a RUSLE model); can also include a frost-risk note naming specific crops if the best growing window found in the weather data still had sub-zero days, a soil-data-estimated note if SoilGrids returned null at this site, a note if a perennial crop (e.g. alfalfa) appears for only one year in the sequence (real perennials are grown for several consecutive years, not replanted annually), and — for `current_rotation` only — a note naming any crop that doesn't appear to have a viable growing window at this site at all. Never empty. |
| `current_rotation[].risks_and_gaps` | array of strings | Same shape as above, plus the climate-mismatch check: `current_rotation` is never passed through the climate-suitability filter (it's what the farmer is already doing, not a candidate we're filtering), so this is the only place that check runs. If a farmer enters a crop with no viable growing window at their site, this flags it explicitly rather than silently scoring it as if it were viable. |
| `excluded_crops` | array | Crops from `data/crops.json` dropped from consideration at this site for being climate-unsuitable (e.g. too cold for maize), each as `{crop, site_mean_temp_c, crop_temp_tolerance_c}`. Worth surfacing in the UI ("X wasn't considered because...") rather than hiding — it's evidence the recommendation is site-checked, not generic. Can be empty. |
| `current_rotation` | object or `null` | Only present if the request included `current_rotation`. Same shape as one entry of `top_rotations`, so the UI can render the farmer's existing practice alongside the recommendations for direct comparison — this satisfies the brief's ask to "compare at least three rotation strategies, including the existing rotation." `null` if the request didn't supply one. |

### Known limitations to design around

- Revenue scoring is a relative yield-based proxy (`revenue_score`/`explanation.revenue_potential`), not a real profit model — it has no commodity price, input cost, or labour in it. If the UI shows a "trade-off" framing (e.g. "regeneration vs. profit"), be careful not to imply this is actual expected income.
- Crop list is currently 6 crops suited to a Central Iowa rotation (`data/crops.json`). The climate-suitability filter (see `excluded_crops`) now checks each crop's temperature tolerance against the site before recommending it, so the engine won't recommend e.g. maize somewhere too cold — but it only checks temperature, not day-length/photoperiod, rainfall seasonality, or frost timing, so a crop passing the filter isn't a full agronomic guarantee for an unfamiliar region.
- The climate filter needs close to a full year of data (`start_date`/`end_date` spanning ~365 days) to reliably find a viable growing window regardless of hemisphere or local planting calendar — a short date range may wrongly exclude a crop that's fine there, just not during the requested window.
- First request for a new `lat`/`lon`/date-range combination will be slower (NASA POWER + SoilGrids API calls); repeat requests for the same inputs are served from a local cache.
- Perennial forage crops (currently alfalfa) are scored per calendar year like an annual, with no concept of "this crop stays in the ground for N years." Since the erosion-protection score favours alfalfa, top-ranked rotations can show it alternating yearly with another crop, which isn't how it's actually grown — see the `single_year_perennial` caveat in `risks_and_gaps`, and `docs/validation.md`.
