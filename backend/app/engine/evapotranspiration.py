"""FAO-56 Penman-Monteith reference evapotranspiration (ET0) and crop water
demand (ETc = Kc x ET0).

Reference: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998).
Crop evapotranspiration - Guidelines for computing crop water requirements.
FAO Irrigation and Drainage Paper 56, chapter 4.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GSC = 0.0820  # solar constant, MJ m-2 min-1


def et0_penman_monteith(power_df: pd.DataFrame, lat_deg: float, elevation_m: float = 300.0) -> pd.Series:
    """Compute daily reference ET0 (mm/day) from NASA POWER daily data.

    Expects power_df to have columns: T2M_MAX, T2M_MIN, T2M, RH2M, WS2M,
    ALLSKY_SFC_SW_DWN (all as returned by nasa_power.fetch_power_daily).
    """
    tmax = power_df["T2M_MAX"].astype(float)
    tmin = power_df["T2M_MIN"].astype(float)
    tmean = power_df["T2M"].astype(float)
    rh_mean = power_df["RH2M"].astype(float)
    u2 = power_df["WS2M"].astype(float)  # POWER wind speed is already at 2m
    rs = power_df["ALLSKY_SFC_SW_DWN"].astype(float)  # MJ m-2 day-1

    # Atmospheric pressure from elevation (FAO-56 eq. 7)
    pressure = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26
    gamma = 0.000665 * pressure  # psychrometric constant, kPa/degC

    # Saturation and actual vapour pressure (FAO-56 eq. 11-19)
    def sat_vp(t):
        return 0.6108 * np.exp(17.27 * t / (t + 237.3))

    es = (sat_vp(tmax) + sat_vp(tmin)) / 2
    ea = sat_vp(tmean) * rh_mean / 100.0

    # Slope of saturation vapour pressure curve (FAO-56 eq. 13)
    delta = 4098 * sat_vp(tmean) / (tmean + 237.3) ** 2

    # Extraterrestrial radiation and clear-sky radiation (FAO-56 eq. 21-28)
    day_of_year = power_df.index.dayofyear
    lat_rad = np.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * day_of_year)
    solar_decl = 0.409 * np.sin(2 * np.pi / 365 * day_of_year - 1.39)
    ws = np.arccos(np.clip(-np.tan(lat_rad) * np.tan(solar_decl), -1, 1))
    ra = (
        (24 * 60 / np.pi)
        * GSC
        * dr
        * (
            ws * np.sin(lat_rad) * np.sin(solar_decl)
            + np.cos(lat_rad) * np.cos(solar_decl) * np.sin(ws)
        )
    )
    rso = (0.75 + 2e-5 * elevation_m) * ra  # clear-sky radiation

    # Net radiation (FAO-56 eq. 38-39)
    albedo = 0.23
    rns = (1 - albedo) * rs
    sigma = 4.903e-9  # Stefan-Boltzmann constant, MJ K-4 m-2 day-1
    tmax_k4 = (tmax + 273.16) ** 4
    tmin_k4 = (tmin + 273.16) ** 4
    rs_rso = (rs / rso).clip(upper=1.0)
    rnl = (
        sigma
        * ((tmax_k4 + tmin_k4) / 2)
        * (0.34 - 0.14 * np.sqrt(ea.clip(lower=0)))
        * (1.35 * rs_rso - 0.35)
    )
    rn = rns - rnl

    soil_heat_flux = 0  # G ~ 0 for daily timestep (FAO-56 eq. 42)

    numerator = 0.408 * delta * (rn - soil_heat_flux) + gamma * (900 / (tmean + 273)) * u2 * (es - ea)
    denominator = delta + gamma * (1 + 0.34 * u2)
    et0 = numerator / denominator
    et0.name = "ET0_mm_day"
    return et0.clip(lower=0)


def crop_coefficient_curve(kc_ini: float, kc_mid: float, kc_end: float, season_length_days: int) -> np.ndarray:
    """Simplified single Kc curve split 20/40/40 into ini/dev+mid/late
    (a common FAO-56 simplification for crops without published stage
    lengths). Returns a daily array of length season_length_days.
    """
    ini_len = max(1, round(season_length_days * 0.2))
    mid_len = max(1, round(season_length_days * 0.4))
    end_len = max(1, season_length_days - ini_len - mid_len)

    kc = np.concatenate([
        np.full(ini_len, kc_ini),
        np.linspace(kc_ini, kc_mid, mid_len),
        np.linspace(kc_mid, kc_end, end_len),
    ])
    return kc[:season_length_days]


def crop_water_demand_mm(et0: pd.Series, crop: dict) -> float:
    """Total seasonal crop water demand (ETc, mm) for one crop, aligning a
    Kc curve to the first `season_length_days` of the given ET0 series.
    """
    season_length = crop["season_length_days"]
    et0_window = et0.iloc[:season_length]
    kc_curve = crop_coefficient_curve(
        crop["kc_ini"], crop["kc_mid"], crop["kc_end"], len(et0_window)
    )
    etc_daily = et0_window.to_numpy() * kc_curve
    return float(np.nansum(etc_daily))
