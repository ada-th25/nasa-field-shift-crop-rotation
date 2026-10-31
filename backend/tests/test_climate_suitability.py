"""Tests for climate suitability filtering, including the sliding-window
fix (an earlier fixed-window version wrongly excluded maize from Iowa
itself) and the current_rotation climate-mismatch check added afterward."""
import pandas as pd
import pytest

from app.engine.climate_suitability import (
    best_growing_window_mean_temp_c,
    climate_mismatched_crops,
    filter_climate_suitable_crops,
    is_climate_suitable,
)

MAIZE = {"min_temp_c": 10, "max_temp_c": 35, "season_length_days": 150, "_name": "maize"}
ALFALFA = {"min_temp_c": 5, "max_temp_c": 30, "season_length_days": 365, "_name": "alfalfa"}


def _seasonal_temp_series(start="2023-01-01", periods=365, winter_temp=-5, summer_temp=22):
    """A full year of daily T2M with a cold winter and a warm summer, like a
    temperate-climate site -- so a sliding window has somewhere warm to find."""
    dates = pd.date_range(start, periods=periods, freq="D")
    doy = dates.dayofyear
    # cosine centered on winter (day 1), peaking warm around day ~200
    import numpy as np
    temps = winter_temp + (summer_temp - winter_temp) * (1 - np.cos(2 * np.pi * (doy - 15) / 365)) / 2
    return pd.DataFrame({"T2M": temps, "T2M_MIN": temps - 5}, index=dates)


def test_fixed_window_would_wrongly_exclude_maize_but_sliding_window_does_not():
    """Regression test for the original bug: a Jan-1-start window lands in
    winter even in a climate where maize grows fine in summer."""
    df = _seasonal_temp_series()
    mean_temp = best_growing_window_mean_temp_c(df, MAIZE)
    assert is_climate_suitable(MAIZE, mean_temp)


def test_cold_climate_excludes_maize():
    df = _seasonal_temp_series(winter_temp=-20, summer_temp=8)  # never reaches maize's 10-35C range
    mean_temp = best_growing_window_mean_temp_c(df, MAIZE)
    assert not is_climate_suitable(MAIZE, mean_temp)


def test_filter_returns_suitable_and_excluded():
    df = _seasonal_temp_series(winter_temp=-20, summer_temp=8)
    crops = {"maize": MAIZE, "alfalfa": {**ALFALFA, "min_temp_c": 5, "max_temp_c": 9}, "_baseline_crop": "maize"}
    suitable, excluded = filter_climate_suitable_crops(crops, df)

    assert "maize" not in suitable
    assert any(e["crop"] == "maize" for e in excluded)
    assert "_baseline_crop" not in suitable and "_baseline_crop" not in [e["crop"] for e in excluded]


def test_climate_mismatched_crops_flags_unsuitable_current_rotation():
    df = _seasonal_temp_series(winter_temp=-20, summer_temp=8)
    mismatched = climate_mismatched_crops([MAIZE, MAIZE, MAIZE], df)

    assert len(mismatched) == 1
    assert mismatched[0]["crop"] == "maize"


def test_climate_mismatched_crops_empty_for_suitable_sequence():
    df = _seasonal_temp_series(winter_temp=-5, summer_temp=22)
    assert climate_mismatched_crops([MAIZE, MAIZE], df) == []


def test_climate_mismatched_crops_deduplicates_repeated_crop():
    df = _seasonal_temp_series(winter_temp=-20, summer_temp=8)
    mismatched = climate_mismatched_crops([MAIZE, MAIZE, MAIZE], df)
    assert len(mismatched) == 1  # not one entry per occurrence
