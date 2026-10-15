"""Client for the NASA POWER daily point API (no API key required).

Docs: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Parameters used downstream: temperature extremes, humidity, wind, solar
# radiation (for FAO-56 Penman-Monteith ET0), precipitation, and the two
# soil-wetness proxies (root-zone and surface) used as a SMAP fallback.
DEFAULT_PARAMETERS = [
    "T2M_MAX",
    "T2M_MIN",
    "T2M",
    "RH2M",
    "WS2M",
    "ALLSKY_SFC_SW_DWN",
    "PRECTOTCORR",
    "GWETROOT",
    "GWETTOP",
]

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"


def _cache_path(lat: float, lon: float, start: str, end: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"power_{lat}_{lon}_{start}_{end}.json"


def fetch_power_daily(
    lat: float,
    lon: float,
    start: str,
    end: str,
    parameters: list[str] | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch daily point data from NASA POWER and return a tidy DataFrame.

    start/end are 'YYYYMMDD' strings. Results are cached to data/cache/ since
    repeated calls during development/demo would otherwise re-hit the API.
    """
    parameters = parameters or DEFAULT_PARAMETERS
    cache_file = _cache_path(lat, lon, start, end)

    if use_cache and cache_file.exists():
        raw = json.loads(cache_file.read_text())
    else:
        response = requests.get(
            POWER_BASE_URL,
            params={
                "parameters": ",".join(parameters),
                "community": "AG",
                "longitude": lon,
                "latitude": lat,
                "start": start,
                "end": end,
                "format": "JSON",
            },
            timeout=30,
        )
        response.raise_for_status()
        raw = response.json()
        cache_file.write_text(json.dumps(raw))

    params_data = raw["properties"]["parameter"]
    df = pd.DataFrame(params_data)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"

    # POWER uses -999 as a fill value for missing days.
    df = df.replace(-999, pd.NA)
    return df


if __name__ == "__main__":
    # Ames, Iowa
    df = fetch_power_daily(lat=42.0308, lon=-93.6319, start="20240101", end="20241231")
    print(df.head())
    print(df.describe())
