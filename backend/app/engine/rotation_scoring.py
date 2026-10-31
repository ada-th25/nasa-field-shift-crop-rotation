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
    soil_carbon_is_estimated: bool = False
    """True when soil_organic_carbon_g_kg is a fallback default, not a real
    SoilGrids reading (e.g. SoilGrids returned null at this site). The
    fallback value used to happen to equal soil_degradation_baseline_g_kg,
    which silently scored every missing-data site as maximally degraded --
    this flag lets soil_score treat a missing reading as neutral instead."""


@dataclass
class RotationWeights:
    soil: float = 0.3
    water: float = 0.3
    resilience: float = 0.15
    revenue: float = 0.25

    def normalized(self) -> "RotationWeights":
        total = self.soil + self.water + self.resilience + self.revenue
        return RotationWeights(
            self.soil / total, self.water / total, self.resilience / total, self.revenue / total
        )


def passes_agronomic_rules(sequence: list[dict], min_family_gap_years: int = 2) -> bool:
    """Hard constraints: don't repeat a crop family within `min_family_gap_years`."""
    families = [crop["crop_family"] for crop in sequence]
    for i, family in enumerate(families):
        window = families[max(0, i - min_family_gap_years + 1):i]
        if family in window:
            return False
    return True


# Qualitative erosion-protection indicator by crop role, NOT a RUSLE
# C-factor -- those are soil/slope/tillage-practice-specific and need
# site-level RUSLE2 modelling (NRCS RUSLE2 Handbook) to get right, and even
# NRCS's own management files are inconsistent for this (Chesapeake Bay
# Program STAC review, 2017). This instead encodes well-documented general
# patterns: continuous perennial cover and dedicated cover crops protect
# soil far better than annual row crops with a bare-soil establishment
# period, and legume row crops like soybean leave less persistent residue
# than grain crops (widely reported corn-vs-soybean erosion comparisons,
# e.g. Iowa State University Extension).
EROSION_PROTECTION_BY_ROLE = {
    "perennial_forage_legume": 1.0,
    "cover_crop": 0.9,
    "cash_grain": 0.5,
    "cash_grain_legume": 0.3,
}


def erosion_protection_score(crop: dict) -> float:
    """0-1 qualitative erosion-protection indicator from role + root habit.
    See EROSION_PROTECTION_BY_ROLE for what this is and isn't."""
    base = EROSION_PROTECTION_BY_ROLE.get(crop.get("role"), 0.5)
    root_bonus = 0.1 if crop.get("root_type", "").startswith("fibrous") else 0.0
    return float(np.clip(base + root_bonus, 0, 1))


def soil_score(crop: dict, prev_crop: dict | None, baseline: EnvironmentalBaseline) -> float:
    """0-1 score: nitrogen contribution + organic carbon headroom + root
    diversity bonus vs. the previous crop + erosion protection."""
    n_component = np.tanh(max(crop["nitrogen_balance_kg_ha"], 0) / 100)

    if baseline.soil_carbon_is_estimated:
        carbon_component = 0.5  # neutral: no real reading to score against
    else:
        carbon_headroom = 1 - min(baseline.soil_organic_carbon_g_kg / baseline.soil_degradation_baseline_g_kg, 1)
        carbon_component = np.clip(carbon_headroom, 0, 1)

    root_bonus = 0.0
    if prev_crop is not None and crop["root_depth_class"] != prev_crop["root_depth_class"]:
        root_bonus = 0.2

    erosion_component = erosion_protection_score(crop)

    score = (
        0.35 * n_component
        + 0.25 * carbon_component
        + 0.15 * (1 if root_bonus else 0)
        + 0.25 * erosion_component
    )
    return float(np.clip(score, 0, 1))


def available_water_mm(baseline: EnvironmentalBaseline) -> float:
    """Rainfall scaled up by how wet the root zone already is -- the same
    'water actually available' estimate used by water_score and the
    per-year explanation, kept in one place so they can't drift apart."""
    return baseline.seasonal_precip_mm * (0.5 + 0.5 * baseline.mean_root_zone_wetness)


def water_score(crop_water_demand_mm: float, baseline: EnvironmentalBaseline) -> float:
    """0-1 score, 1 = demand comfortably covered by rainfall + stored soil
    moisture, 0 = severe deficit."""
    deficit = max(crop_water_demand_mm - available_water_mm(baseline), 0)
    water_deficit_index = deficit / max(crop_water_demand_mm, 1)
    return float(np.clip(1 - water_deficit_index, 0, 1))


def resilience_score(crop: dict) -> float:
    """0-1 score from the crop's published drought tolerance."""
    mapping = {"low": 0.2, "medium": 0.6, "high": 1.0}
    return mapping.get(crop.get("drought_tolerance", "medium"), 0.5)


def revenue_score(crop: dict) -> float:
    """0-1 relative revenue-potential proxy -- NOT a profit calculation.
    Crops with no market revenue (e.g. a cover crop terminated before
    harvest) score 0. Others score from typical_yield_t_ha, a stable
    multi-year-average order of magnitude, deliberately NOT combined with
    a commodity price: real prices are volatile month to month and even
    USDA's own 2024 figures for the same crop were inconsistent across
    reports depending on when they were pulled, so a fixed $/unit here
    would be a precision claim this project can't back up. tanh(yield / 8)
    scales the current crop set's yield range (2.4-11 t/ha) into 0-1
    without needing a price."""
    if not crop.get("has_market_revenue", True):
        return 0.0
    yield_t_ha = crop.get("typical_yield_t_ha") or 0.0
    return float(np.clip(np.tanh(yield_t_ha / 8), 0, 1))


def explain_year(
    crop: dict, prev_crop: dict | None, water_demand_mm: float, baseline: EnvironmentalBaseline
) -> dict:
    """Real-unit, plain-language explanation of why this crop scored the
    way it did in this year of the rotation -- the 0-1 scores in
    year_breakdown aren't meaningful to a farmer on their own, this is the
    'why' layer on top of them. Deliberately doesn't claim a soil nitrogen
    *stock* change (we don't model a running soil N pool), only this
    crop's own net N balance for the year.
    """
    n_balance = crop["nitrogen_balance_kg_ha"]
    water_deficit_mm = round(max(water_demand_mm - available_water_mm(baseline), 0), 1)
    root_diversified = prev_crop is not None and crop["root_depth_class"] != prev_crop["root_depth_class"]
    drought_tolerance = crop.get("drought_tolerance", "medium")
    erosion_score = erosion_protection_score(crop)
    erosion_level = "high" if erosion_score >= 0.75 else "medium" if erosion_score >= 0.45 else "low"
    rev_score = revenue_score(crop)
    revenue_level = "none" if rev_score == 0 else "high" if rev_score >= 0.75 else "medium" if rev_score >= 0.45 else "low"

    sentences = []
    if n_balance > 0:
        sentences.append(
            f"Adds an estimated {n_balance:.0f} kg N/ha to the soil, reducing fertilizer need for the next crop."
        )
    elif n_balance < 0:
        sentences.append(
            f"Draws down an estimated {abs(n_balance):.0f} kg N/ha of soil nitrogen; will need fertilizer input."
        )
    else:
        sentences.append("Roughly nitrogen-neutral for the soil.")

    if water_deficit_mm > 0:
        sentences.append(
            f"Water demand (~{water_demand_mm:.0f} mm) exceeds expected rainfall and stored soil "
            f"moisture by ~{water_deficit_mm:.0f} mm; irrigation may be needed."
        )
    else:
        sentences.append(
            f"Water demand (~{water_demand_mm:.0f} mm) is comfortably covered by expected rainfall "
            "and stored soil moisture."
        )

    if root_diversified:
        sentences.append(
            "Different rooting depth than the previous crop, helping break up compaction and "
            "access a different soil moisture layer."
        )

    sentences.append(f"{drought_tolerance.capitalize()} drought tolerance.")
    sentences.append(f"{erosion_level.capitalize()} erosion protection from ground cover and residue.")
    if revenue_level == "none":
        sentences.append("Grown for soil benefit, not sold into a market -- no direct harvest revenue.")
    else:
        sentences.append(f"{revenue_level.capitalize()} relative revenue potential based on typical yield.")

    return {
        "nitrogen_balance_kg_ha": n_balance,
        "water_demand_mm": round(water_demand_mm, 1),
        "water_deficit_mm": water_deficit_mm,
        "root_diversified_from_previous": root_diversified,
        "drought_tolerance": drought_tolerance,
        "erosion_protection": erosion_level,
        "revenue_potential": revenue_level,
        "summary": " ".join(sentences),
    }


def compute_impact_metrics(
    sequence: list[dict],
    water_demands_mm: list[float],
    baseline_crop: dict,
    baseline_water_demand_mm: float,
) -> dict:
    """Compare a candidate rotation against a continuous-monoculture baseline
    (the same crop grown every year, e.g. continuous maize) in real units,
    rather than the abstract 0-1 scores. Framed against UN SDGs the numbers
    plausibly support: SDG 6 (Clean Water), SDG 13 (Climate Action, via
    avoided synthetic nitrogen), SDG 15 (Life on Land, via soil organic
    carbon / nitrogen balance), SDG 2 (Zero Hunger, via resilience and
    nitrogen self-sufficiency). Tags are only attached when the rotation
    actually improves on the baseline for that metric, not asserted
    unconditionally.
    """
    length = len(sequence)

    rotation_n_total = sum(c["nitrogen_balance_kg_ha"] for c in sequence)
    baseline_n_total = baseline_crop["nitrogen_balance_kg_ha"] * length
    nitrogen_fertilizer_avoided_kg_ha = round(rotation_n_total - baseline_n_total, 1)

    rotation_water_total = sum(water_demands_mm)
    baseline_water_total = baseline_water_demand_mm * length
    water_saved_mm = round(baseline_water_total - rotation_water_total, 1)
    water_saved_pct = round(100 * water_saved_mm / baseline_water_total, 1) if baseline_water_total else 0.0

    sdg_tags = []
    if water_saved_mm > 0:
        sdg_tags.append({
            "sdg": "SDG 6",
            "label": "Clean Water and Sanitation",
            "rationale": f"Uses ~{water_saved_mm:.0f} mm less water than continuous {baseline_crop['_name']} over {length} years.",
        })
    if nitrogen_fertilizer_avoided_kg_ha > 0:
        sdg_tags.append({
            "sdg": "SDG 13",
            "label": "Climate Action",
            "rationale": f"Avoids ~{nitrogen_fertilizer_avoided_kg_ha:.0f} kg/ha of synthetic nitrogen vs. continuous {baseline_crop['_name']}, reducing fertilizer-linked emissions.",
        })
        sdg_tags.append({
            "sdg": "SDG 15",
            "label": "Life on Land",
            "rationale": "Net positive nitrogen balance supports soil biological activity and organic matter vs. a nitrogen-depleting monoculture.",
        })

    return {
        "baseline": f"continuous {baseline_crop['_name']}",
        "nitrogen_fertilizer_avoided_kg_ha": nitrogen_fertilizer_avoided_kg_ha,
        "water_saved_mm": water_saved_mm,
        "water_saved_pct": water_saved_pct,
        "sdg_tags": sdg_tags,
    }


def single_year_perennials(sequence: list[dict]) -> list[str]:
    """Perennial crops (e.g. alfalfa) that appear for only one year in a row
    in this sequence. Real perennial forage is established once and kept in
    the ground for several years -- a sequence that plants and replaces it
    annually isn't how it's actually grown, and establishment-year yield
    drag/cost isn't modelled here."""
    names = []
    for i, crop in enumerate(sequence):
        if crop.get("role") != "perennial_forage_legume":
            continue
        prev_same = i > 0 and sequence[i - 1].get("_name") == crop.get("_name")
        next_same = i < len(sequence) - 1 and sequence[i + 1].get("_name") == crop.get("_name")
        if not prev_same and not next_same:
            names.append(crop.get("_name", "unknown"))
    return list(dict.fromkeys(names))


def generate_risks_and_gaps(
    frost_risk_crops: list[str],
    soil_is_estimated: bool,
    single_year_perennial_crops: list[str] | None = None,
    climate_mismatched_crops: list[dict] | None = None,
) -> list[str]:
    """Per-rotation caveats surfaced directly in the API response, not just
    in docs -- what the brief calls 'information gaps' and 'risks that would
    need local review by farmers or agricultural experts'. Always includes
    the three gaps that apply to every rotation this engine produces, plus
    any rotation-specific flags."""
    risks = [
        "Climate suitability is checked on temperature only -- day length, frost timing, rainfall "
        "seasonality, and local pest or disease pressure aren't modelled. Have an agronomist confirm "
        "this rotation suits local conditions before adopting it.",
        "Revenue potential is a relative, yield-based proxy, not a real profit calculation -- it "
        "excludes commodity price, input costs, and labour, all of which vary too much by region and "
        "season to responsibly estimate here.",
        "Erosion protection is a qualitative indicator based on crop role and root habit, not a "
        "site-specific soil-loss model (e.g. RUSLE2) -- slope, tillage practice, and residue "
        "management all affect real erosion risk and aren't accounted for here.",
    ]
    if frost_risk_crops:
        risks.append(
            f"{', '.join(frost_risk_crops)}: the best available growing window in the fetched "
            "weather data still included sub-zero days. Check local frost dates before planting."
        )
    if soil_is_estimated:
        risks.append(
            "Soil texture, pH, and organic carbon data weren't available at this exact location; a "
            "generic estimate was used instead. A local soil test is recommended."
        )
    if single_year_perennial_crops:
        risks.append(
            f"{', '.join(single_year_perennial_crops)} is shown here for a single year, but in "
            "practice a perennial forage crop like this is established once and kept in the ground "
            "for several years, not replanted annually -- this rotation doesn't model establishment "
            "cost or yield drag from doing that."
        )
    if climate_mismatched_crops:
        for m in climate_mismatched_crops:
            lo, hi = m["crop_temp_tolerance_c"]
            risks.append(
                f"{m['crop']} doesn't appear to have a viable growing window at this site (site mean "
                f"~{m['site_mean_temp_c']}C vs. a tolerance of [{lo}, {hi}]C) -- this score may not "
                "reflect whether this crop can actually be grown here."
            )
    return risks


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
        s_revenue = revenue_score(crop)
        year_total = (
            weights.soil * s_soil
            + weights.water * s_water
            + weights.resilience * s_resilience
            + weights.revenue * s_revenue
        )
        year_scores.append({
            "crop": crop.get("_name", "unknown"),
            "soil_score": round(s_soil, 3),
            "water_score": round(s_water, 3),
            "resilience_score": round(s_resilience, 3),
            "revenue_score": round(s_revenue, 3),
            "year_score": round(year_total, 3),
            "explanation": explain_year(crop, prev_crop, water_demands_mm[year_idx], baseline),
        })

    discounted_total = sum(
        (discount ** i) * y["year_score"] for i, y in enumerate(year_scores)
    )
    return {
        "sequence": [c.get("_name", "unknown") for c in sequence],
        "rsi": round(discounted_total, 3),
        "year_breakdown": year_scores,
    }
