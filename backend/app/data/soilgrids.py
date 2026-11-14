"""Client for ISRIC SoilGrids v2.0 REST API (not a NASA dataset, but the
standard global soil property source; used for local soil context).

Docs: https://www.isric.org/explore/soilgrids/faq-soilgrids#What_do_the_filenames_mean
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

SOILGRIDS_BASE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# Topsoil (0-5cm) mean values for the properties the scoring engine needs.
DEFAULT_PROPERTIES = ["clay", "sand", "phh2o", "soc"]
DEFAULT_DEPTH = "0-5cm"
DEFAULT_VALUE = "mean"

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"

# SoilGrids reports most properties in tenths of their conventional unit
# (e.g. g/kg*10 for soc, %*10 for clay/sand, pH*10). This converts to
# conventional units (soc in g/kg, clay/sand in %, phh2o in pH).
_CONVERSION_FACTOR = {
    "clay": 0.1,
    "sand": 0.1,
    "phh2o": 0.1,
    "soc": 0.1,
}


def _cache_path(lat: float, lon: float) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"soilgrids_{lat}_{lon}.json"


def _query_soilgrids(lat: float, lon: float, properties: list[str]) -> dict:
    response = requests.get(
        SOILGRIDS_BASE_URL,
        params={
            "lon": lon,
            "lat": lat,
            "property": properties,
            "depth": DEFAULT_DEPTH,
            "value": DEFAULT_VALUE,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _parse_soilgrids(raw: dict) -> dict:
    result = {}
    for layer in raw["properties"]["layers"]:
        name = layer["name"]
        depth_entry = next(
            d for d in layer["depths"] if d["label"] == DEFAULT_DEPTH
        )
        value = depth_entry["values"][DEFAULT_VALUE]
        if value is not None:
            value = value * _CONVERSION_FACTOR.get(name, 1)
        result[name] = value

    return {
        "clay_pct": result.get("clay"),
        "sand_pct": result.get("sand"),
        "ph": result.get("phh2o"),
        "soc_g_kg": result.get("soc"),
    }


def fetch_soilgrids(
    lat: float,
    lon: float,
    properties: list[str] | None = None,
    use_cache: bool = True,
    max_retries: int = 2,
) -> dict:
    """Fetch topsoil properties for a point and return a flat dict,
    e.g. {"clay_pct": 24.3, "sand_pct": 38.1, "ph": 6.4, "soc_g_kg": 18.2}.

    Observed live (see docs/algorithm.md §13): the REST query endpoint
    sometimes returns a valid 200 response with every property null for a
    point that other nearby points resolve fine -- not an error we can
    catch, just an empty answer. A couple of quick retries costs little and
    recovers some of those; if it's still null after `max_retries`, this
    returns the null result as-is and the caller's existing
    soil_carbon_is_estimated fallback takes over.
    """
    properties = properties or DEFAULT_PROPERTIES
    cache_file = _cache_path(lat, lon)

    if use_cache and cache_file.exists():
        return _parse_soilgrids(json.loads(cache_file.read_text()))

    raw = _query_soilgrids(lat, lon, properties)
    parsed = _parse_soilgrids(raw)
    attempt = 0
    while parsed.get("soc_g_kg") is None and attempt < max_retries:
        time.sleep(1.5)
        raw = _query_soilgrids(lat, lon, properties)
        parsed = _parse_soilgrids(raw)
        attempt += 1

    cache_file.write_text(json.dumps(raw))
    return parsed


if __name__ == "__main__":
    print(fetch_soilgrids(lat=42.0308, lon=-93.6319))
