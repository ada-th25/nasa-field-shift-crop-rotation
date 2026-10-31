"""Tests for the FAO-56 Penman-Monteith ET0 implementation.

The main test here checks our implementation against FAO-56's own published
worked example (Example 18: Uccle, Brussels, 6 July), not just internal
consistency -- real-world verification against the textbook, confirmed by
fetching the actual FAO document rather than assumed from memory.
"""
import pandas as pd
import pytest

from app.engine.evapotranspiration import crop_coefficient_curve, et0_penman_monteith


def test_et0_matches_fao56_worked_example():
    """FAO-56 (Allen et al., 1998), chapter 4, Example 18: Uccle, Brussels,
    Belgium, 6 July. Textbook result: ETo = 3.9 mm/day (3.88 unrounded).

    Our implementation uses mean RH2M (NASA POWER's only humidity field)
    rather than FAO-56's separate RHmax/RHmin -- a known simplification,
    approximated here with the average of the textbook's RHmax/RHmin. The
    tolerance below reflects that approximation, not a loose pass bar: the
    actual result (3.867 mm/day) came within 0.35% of the textbook figure
    when this was checked.
    """
    df = pd.DataFrame(
        {
            "T2M_MAX": [21.5],
            "T2M_MIN": [12.3],
            "T2M": [16.9],
            "RH2M": [(84 + 63) / 2],
            "WS2M": [2.078],
            "ALLSKY_SFC_SW_DWN": [22.07],
        },
        index=pd.to_datetime(["2024-07-06"]),
    )

    result = et0_penman_monteith(df, lat_deg=50.80, elevation_m=100)

    assert result.iloc[0] == pytest.approx(3.88, abs=0.1)


def test_et0_never_negative():
    """A pathological input (near-freezing, no sun, high humidity) shouldn't
    produce a negative ET0 -- the function clips to zero, this confirms it."""
    df = pd.DataFrame(
        {
            "T2M_MAX": [1.0],
            "T2M_MIN": [-2.0],
            "T2M": [-0.5],
            "RH2M": [98.0],
            "WS2M": [0.1],
            "ALLSKY_SFC_SW_DWN": [0.5],
        },
        index=pd.to_datetime(["2024-01-15"]),
    )

    result = et0_penman_monteith(df, lat_deg=60.0, elevation_m=10)

    assert (result >= 0).all()


def test_crop_coefficient_curve_shape():
    """The Kc curve should start at kc_ini, end at kc_end, and have exactly
    season_length_days entries."""
    curve = crop_coefficient_curve(kc_ini=0.3, kc_mid=1.2, kc_end=0.6, season_length_days=150)

    assert len(curve) == 150
    assert curve[0] == pytest.approx(0.3)
    assert curve[-1] == pytest.approx(0.6)
    assert curve.max() <= 1.2 + 1e-9


def test_crop_coefficient_curve_short_season():
    """A very short season shouldn't produce a zero-length or malformed
    curve -- each stage is clamped to at least 1 day."""
    curve = crop_coefficient_curve(kc_ini=0.3, kc_mid=1.0, kc_end=0.5, season_length_days=3)

    assert len(curve) == 3
