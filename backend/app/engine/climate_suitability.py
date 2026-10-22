"""Climate suitability filter.

Without this, the candidate generator would happily rank rotations using
crops that can't actually grow at the queried site (e.g. alfalfa in a
desert, or maize somewhere too cold) — the engine would look like it works
globally without actually checking. This filters the crop pool to a given
site's observed temperature before candidates are ever generated.

This deliberately does NOT assume the growing season starts on the caller's
`start_date` (an earlier version did, and it wrongly excluded maize from
Iowa itself, because a Jan-1-start window lands in winter). Instead it
slides a season-length window across the whole fetched period and asks "is
there *any* stretch in this period warm/cool enough for this crop" — i.e.
does a viable planting window exist at all, not "is the requested date
range itself a good planting window". This needs at least a season's worth
of data to find a viable window; fetching close to a full year is the safe
default regardless of hemisphere or local planting calendar.
"""
from __future__ import annotations

import pandas as pd


def best_growing_window_mean_temp_c(power_df: pd.DataFrame, crop: dict) -> float:
    """Mean T2M of whichever season-length window in the fetched period is
    closest to the crop's ideal temperature midpoint — i.e. the best-case
    planting window available in the data, not a fixed start date."""
    season_length = crop["season_length_days"]
    temps = power_df["T2M"].dropna()
    if len(temps) < season_length:
        return float(temps.mean())

    rolling_means = temps.rolling(window=season_length).mean().dropna()
    crop_mid_temp = (crop["min_temp_c"] + crop["max_temp_c"]) / 2
    closest_idx = (rolling_means - crop_mid_temp).abs().idxmin()
    return float(rolling_means.loc[closest_idx])


def is_climate_suitable(crop: dict, mean_temp_c: float) -> bool:
    return crop["min_temp_c"] <= mean_temp_c <= crop["max_temp_c"]


def filter_climate_suitable_crops(crops: dict, power_df: pd.DataFrame) -> tuple[dict, list[dict]]:
    """Split a crops dict (as loaded from crops.json, including its `_`
    metadata keys) into (suitable_crops, excluded) for this site's weather.

    suitable_crops has the same shape as the input but only the crops that
    passed, metadata keys dropped. excluded lists what was dropped and why,
    for transparency in the API response.
    """
    suitable = {}
    excluded = []
    for name, crop in crops.items():
        if name.startswith("_"):
            continue
        mean_temp = best_growing_window_mean_temp_c(power_df, crop)
        if is_climate_suitable(crop, mean_temp):
            suitable[name] = crop
        else:
            excluded.append({
                "crop": name,
                "site_mean_temp_c": round(mean_temp, 1),
                "crop_temp_tolerance_c": [crop["min_temp_c"], crop["max_temp_c"]],
            })
    return suitable, excluded
