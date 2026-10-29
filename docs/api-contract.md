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
  "priority_weights": { "soil": 0.4, "water": 0.4, "resilience": 0.2 },
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
| `priority_weights` | object | Keys `soil`, `water`, `resilience` (farmer priority sliders). Don't need to sum to 1, they're normalized server-side. |
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
      "sequence": ["cereal_rye_cover", "soybean", "cereal_rye_cover"],
      "rsi": 1.795,
      "year_breakdown": [
        {
          "crop": "cereal_rye_cover",
          "soil_score": 0.05,
          "water_score": 1.0,
          "resilience_score": 1.0,
          "year_score": 0.62,
          "explanation": {
            "nitrogen_balance_kg_ha": 10,
            "water_demand_mm": 253.4,
            "water_deficit_mm": 0,
            "root_diversified_from_previous": false,
            "drought_tolerance": "high",
            "summary": "Adds an estimated 10 kg N/ha to the soil, reducing fertilizer need for the next crop. Water demand (~253 mm) is comfortably covered by expected rainfall and stored soil moisture. High drought tolerance."
          }
        }
      ],
      "impact_metrics": {
        "baseline": "continuous maize",
        "nitrogen_fertilizer_avoided_kg_ha": 510,
        "water_saved_mm": 192.4,
        "water_saved_pct": 22.5,
        "sdg_tags": [
          {
            "sdg": "SDG 6",
            "label": "Clean Water and Sanitation",
            "rationale": "Uses ~192 mm less water than continuous maize over 3 years."
          }
        ]
      },
      "risks_and_gaps": [
        "Climate suitability is checked on temperature only -- day length, frost timing, rainfall seasonality, and local pest or disease pressure aren't modelled. Have an agronomist confirm this rotation suits local conditions before adopting it.",
        "No profit, yield, or market-price dimension is scored yet -- this rotation is ranked on soil health, water, and drought resilience only, not expected income."
      ]
    }
  ],
  "current_rotation": {
    "sequence": ["maize"],
    "rsi": 0.44,
    "year_breakdown": [ "...same shape as top_rotations[].year_breakdown..." ],
    "impact_metrics": { "baseline": "continuous maize", "nitrogen_fertilizer_avoided_kg_ha": 0, "water_saved_mm": 0.0, "water_saved_pct": 0.0, "sdg_tags": [] },
    "risks_and_gaps": [ "...same two always-on gaps as above..." ]
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `soil.clay_pct`, `soil.sand_pct` | float, % | Topsoil (0-5cm) texture, from SoilGrids. **Can be `null`** — SoilGrids has gaps at some real-world points (e.g. high-latitude/coastal sites); handle null in the UI rather than assuming a number. |
| `soil.ph` | float or null | Topsoil pH. Same null caveat as above. |
| `soil.soc_g_kg` | float or null | Soil organic carbon, g/kg. Same null caveat as above. |
| `mean_et0_mm_day` | float | Average daily reference evapotranspiration over the requested date window. Informational — a high-level water-demand signal for the UI. |
| `top_rotations` | array | Ranked highest RSI first. |
| `top_rotations[].sequence` | array of strings | Crop names in year order, matching keys in `data/crops.json`. |
| `top_rotations[].rsi` | float | Rotational Suitability Index — the overall ranking score. Not bounded to a fixed range (it's a discounted sum across years), higher is better, only meaningful relative to other rotations in the same response. |
| `top_rotations[].year_breakdown` | array | One entry per year of the sequence, each 0-1 sub-score plus that year's combined score. Useful if the UI wants to show *why* a rotation ranked well (e.g. a bar chart per year). |
| `year_breakdown[].explanation` | object | The 0-1 scores translated into real units and plain language, for showing a farmer *why* — not just "soil_score: 0.39" but "adds ~40 kg N/ha". Fields: `nitrogen_balance_kg_ha` (this crop's own net N for the year, not a cumulative soil N stock — we don't model that), `water_demand_mm`, `water_deficit_mm` (0 if demand is covered by expected rainfall/soil moisture), `root_diversified_from_previous` (bool), `drought_tolerance`, and `summary` (a ready-to-display sentence, or build your own from the fields). |
| `top_rotations[].impact_metrics` | object | This rotation vs. a continuous-monoculture baseline (currently `data/crops.json`'s `_baseline_crop`, "maize"), in real units rather than abstract scores. |
| `impact_metrics.water_saved_mm`, `.water_saved_pct` | float | Water demand avoided vs. the baseline over the full sequence. Can be negative (the rotation uses *more* water than the baseline, e.g. a sequence including alfalfa) — don't clamp this to zero in the UI, a negative value is a real and useful signal. |
| `impact_metrics.nitrogen_fertilizer_avoided_kg_ha` | float | Net synthetic nitrogen avoided vs. the baseline, summed over the sequence. Can also be negative. |
| `impact_metrics.sdg_tags` | array | Zero or more of `{sdg, label, rationale}`, only included when the rotation actually improves on the baseline for that metric — this list can be empty for a rotation that doesn't outperform the baseline on any tracked metric. Don't assume every rotation has at least one tag. |
| `top_rotations[].risks_and_gaps` | array of strings | Plain-language caveats for this specific rotation — what the challenge brief calls "information gaps" and "risks that would need local review." Always includes two general caveats (climate check is temperature-only; no profit/yield scoring yet); can also include a frost-risk note naming specific crops if the best growing window found in the weather data still had sub-zero days, and a soil-data-estimated note if SoilGrids returned null at this site. Never empty. |
| `excluded_crops` | array | Crops from `data/crops.json` dropped from consideration at this site for being climate-unsuitable (e.g. too cold for maize), each as `{crop, site_mean_temp_c, crop_temp_tolerance_c}`. Worth surfacing in the UI ("X wasn't considered because...") rather than hiding — it's evidence the recommendation is site-checked, not generic. Can be empty. |
| `current_rotation` | object or `null` | Only present if the request included `current_rotation`. Same shape as one entry of `top_rotations`, so the UI can render the farmer's existing practice alongside the recommendations for direct comparison — this satisfies the brief's ask to "compare at least three rotation strategies, including the existing rotation." `null` if the request didn't supply one. |

### Known limitations to design around

- No profit/yield dimension yet — scores only reflect soil health, water, and drought resilience. If the UI shows a "trade-off" framing (e.g. "regeneration vs. profit"), the profit side isn't implemented yet.
- Crop list is currently 6 crops suited to a Central Iowa rotation (`data/crops.json`). The climate-suitability filter (see `excluded_crops`) now checks each crop's temperature tolerance against the site before recommending it, so the engine won't recommend e.g. maize somewhere too cold — but it only checks temperature, not day-length/photoperiod, rainfall seasonality, or frost timing, so a crop passing the filter isn't a full agronomic guarantee for an unfamiliar region.
- The climate filter needs close to a full year of data (`start_date`/`end_date` spanning ~365 days) to reliably find a viable growing window regardless of hemisphere or local planting calendar — a short date range may wrongly exclude a crop that's fine there, just not during the requested window.
- First request for a new `lat`/`lon`/date-range combination will be slower (NASA POWER + SoilGrids API calls); repeat requests for the same inputs are served from a local cache.
