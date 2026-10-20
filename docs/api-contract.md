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
  "top_n": 5
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
          "year_score": 0.62
        }
      ]
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `soil.clay_pct`, `soil.sand_pct` | float, % | Topsoil (0-5cm) texture, from SoilGrids. |
| `soil.ph` | float | Topsoil pH. |
| `soil.soc_g_kg` | float | Soil organic carbon, g/kg. |
| `mean_et0_mm_day` | float | Average daily reference evapotranspiration over the requested date window. Informational — a high-level water-demand signal for the UI. |
| `top_rotations` | array | Ranked highest RSI first. |
| `top_rotations[].sequence` | array of strings | Crop names in year order, matching keys in `data/crops.json`. |
| `top_rotations[].rsi` | float | Rotational Suitability Index — the overall ranking score. Not bounded to a fixed range (it's a discounted sum across years), higher is better, only meaningful relative to other rotations in the same response. |
| `top_rotations[].year_breakdown` | array | One entry per year of the sequence, each 0-1 sub-score plus that year's combined score. Useful if the UI wants to show *why* a rotation ranked well (e.g. a bar chart per year). |

### Known limitations to design around

- No profit/yield dimension yet — scores only reflect soil health, water, and drought resilience. If the UI shows a "trade-off" framing (e.g. "regeneration vs. profit"), the profit side isn't implemented yet.
- Crop list is currently 6 crops suited to a Central Iowa rotation (`data/crops.json`). Requesting a location far from Iowa will still run, but the candidate crops won't make agronomic sense for that climate yet.
- First request for a new `lat`/`lon`/date-range combination will be slower (NASA POWER + SoilGrids API calls); repeat requests for the same inputs are served from a local cache.
