"""Multi-criteria rotation scoring.

Deliberately simplified vs. a full sigmoid/penalty RSI formula: every
component is normalized to a 0-1 score, hard agronomic rules are applied as
a pre-filter (not a soft penalty), and the final score is a weighted sum.
Easier to explain in a demo and to unit test, same underlying agronomy.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class EnvironmentalBaseline:
    """Site-level numbers fetched from NASA POWER / SoilGrids for one farm."""

    seasonal_precip_mm: float
    mean_root_zone_wetness: float  # GWETROOT, 0-1 fraction of saturation
    soil_organic_carbon_g_kg: float
    soil_degradation_baseline_g_kg: float = 15.0  # a reasonable depleted-soil reference


@dataclass
class RotationWeights:
    soil: float = 0.4
    water: float = 0.4
    resilience: float = 0.2

    def normalized(self) -> "RotationWeights":
        total = self.soil + self.water + self.resilience
        return RotationWeights(self.soil / total, self.water / total, self.resilience / total)


def passes_agronomic_rules(sequence: list[dict], min_family_gap_years: int = 2) -> bool:
    """Hard constraints: don't repeat a crop family within `min_family_gap_years`."""
    families = [crop["crop_family"] for crop in sequence]
    for i, family in enumerate(families):
        window = families[max(0, i - min_family_gap_years + 1):i]
        if family in window:
            return False
    return True


def soil_score(crop: dict, prev_crop: dict | None, baseline: EnvironmentalBaseline) -> float:
    """0-1 score: nitrogen contribution + organic carbon headroom + root
    diversity bonus vs. the previous crop in the sequence."""
    n_component = np.tanh(max(crop["nitrogen_balance_kg_ha"], 0) / 100)

    carbon_headroom = 1 - min(baseline.soil_organic_carbon_g_kg / baseline.soil_degradation_baseline_g_kg, 1)
    carbon_component = np.clip(carbon_headroom, 0, 1)

    root_bonus = 0.0
    if prev_crop is not None and crop["root_depth_class"] != prev_crop["root_depth_class"]:
        root_bonus = 0.2

    score = 0.5 * n_component + 0.3 * carbon_component + 0.2 * (1 if root_bonus else 0)
    return float(np.clip(score, 0, 1))


def water_score(crop_water_demand_mm: float, baseline: EnvironmentalBaseline) -> float:
    """0-1 score, 1 = demand comfortably covered by rainfall + stored soil
    moisture, 0 = severe deficit."""
    available_water = baseline.seasonal_precip_mm * (0.5 + 0.5 * baseline.mean_root_zone_wetness)
    deficit = max(crop_water_demand_mm - available_water, 0)
    water_deficit_index = deficit / max(crop_water_demand_mm, 1)
    return float(np.clip(1 - water_deficit_index, 0, 1))


def resilience_score(crop: dict) -> float:
    """0-1 score from the crop's published drought tolerance."""
    mapping = {"low": 0.2, "medium": 0.6, "high": 1.0}
    return mapping.get(crop.get("drought_tolerance", "medium"), 0.5)


def score_sequence(
    sequence: list[dict],
    baseline: EnvironmentalBaseline,
    water_demands_mm: list[float],
    weights: RotationWeights,
) -> dict:
    """Score one candidate crop sequence. water_demands_mm must align 1:1
    with `sequence` (computed upstream via evapotranspiration.crop_water_demand_mm).
    """
    weights = weights.normalized()
    discount = 0.9  # prioritizes near-term soil/water impact over later years

    year_scores = []
    for year_idx, crop in enumerate(sequence):
        prev_crop = sequence[year_idx - 1] if year_idx > 0 else None
        s_soil = soil_score(crop, prev_crop, baseline)
        s_water = water_score(water_demands_mm[year_idx], baseline)
        s_resilience = resilience_score(crop)
        year_total = weights.soil * s_soil + weights.water * s_water + weights.resilience * s_resilience
        year_scores.append({
            "crop": crop.get("_name", "unknown"),
            "soil_score": round(s_soil, 3),
            "water_score": round(s_water, 3),
            "resilience_score": round(s_resilience, 3),
            "year_score": round(year_total, 3),
        })

    discounted_total = sum(
        (discount ** i) * y["year_score"] for i, y in enumerate(year_scores)
    )
    return {
        "sequence": [c.get("_name", "unknown") for c in sequence],
        "rsi": round(discounted_total, 3),
        "year_breakdown": year_scores,
    }
