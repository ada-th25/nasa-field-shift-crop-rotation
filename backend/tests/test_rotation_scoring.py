"""Tests for the MCDA scoring engine: bounds, edge cases, and the two bugs
fixed after cross-checking real site numbers (soil-carbon neutral-on-missing,
and that revenue/erosion components behave as documented).
"""
import pytest

from app.engine.rotation_scoring import (
    EnvironmentalBaseline,
    RotationWeights,
    bare_field_days_in_year,
    compute_impact_metrics,
    erosion_protection_score,
    generate_risks_and_gaps,
    passes_agronomic_rules,
    resilience_score,
    revenue_score,
    single_year_perennials,
    soil_score,
    water_score,
)

MAIZE = {
    "crop_family": "Poaceae", "nitrogen_balance_kg_ha": -150, "root_type": "fibrous_shallow",
    "root_depth_class": 1, "drought_tolerance": "low", "role": "cash_grain",
    "has_market_revenue": True, "typical_yield_t_ha": 11.0, "season_length_days": 150, "_name": "maize",
}
SOYBEAN = {
    "crop_family": "Fabaceae", "nitrogen_balance_kg_ha": 40, "root_type": "taproot_medium",
    "root_depth_class": 2, "drought_tolerance": "medium", "role": "cash_grain_legume",
    "has_market_revenue": True, "typical_yield_t_ha": 3.4, "season_length_days": 120, "_name": "soybean",
}
RYE_COVER = {
    "crop_family": "Poaceae", "nitrogen_balance_kg_ha": 10, "root_type": "fibrous_deep",
    "root_depth_class": 3, "drought_tolerance": "high", "role": "cover_crop",
    "has_market_revenue": False, "typical_yield_t_ha": None, "season_length_days": 150, "_name": "cereal_rye_cover",
}
ALFALFA = {
    "crop_family": "Fabaceae", "nitrogen_balance_kg_ha": 150, "root_type": "taproot_deep",
    "root_depth_class": 4, "drought_tolerance": "high", "role": "perennial_forage_legume",
    "has_market_revenue": True, "typical_yield_t_ha": 7.6, "season_length_days": 365, "_name": "alfalfa",
}
LENTIL = {
    "crop_family": "Fabaceae", "nitrogen_balance_kg_ha": 25, "root_type": "taproot_medium",
    "root_depth_class": 2, "drought_tolerance": "medium", "role": "cash_grain_legume",
    "has_market_revenue": True, "typical_yield_t_ha": 1.2, "_name": "lentil",
}
CHICKPEA = {
    "crop_family": "Fabaceae", "nitrogen_balance_kg_ha": 35, "root_type": "taproot_deep",
    "root_depth_class": 3, "drought_tolerance": "high", "role": "cash_grain_legume",
    "has_market_revenue": True, "typical_yield_t_ha": 1.4, "_name": "chickpea",
}
RICE = {
    "crop_family": "Poaceae", "flood_irrigated": True, "nitrogen_balance_kg_ha": -170,
    "root_type": "fibrous_shallow", "root_depth_class": 1, "drought_tolerance": "low",
    "role": "cash_grain", "has_market_revenue": True, "typical_yield_t_ha": 8.6,
    "season_length_days": 150, "_name": "rice",
}
SORGHUM = {
    "crop_family": "Poaceae", "nitrogen_balance_kg_ha": -50, "root_type": "fibrous_deep",
    "root_depth_class": 3, "drought_tolerance": "high", "role": "cash_grain",
    "has_market_revenue": True, "typical_yield_t_ha": 3.3, "season_length_days": 130,
    "_name": "sorghum",
}


def baseline(**overrides):
    defaults = dict(seasonal_precip_mm=600.0, mean_root_zone_wetness=0.5, soil_organic_carbon_g_kg=30.0)
    defaults.update(overrides)
    return EnvironmentalBaseline(**defaults)


class TestAgronomicRules:
    def test_rejects_immediate_repeat(self):
        assert not passes_agronomic_rules([MAIZE, MAIZE, SOYBEAN], min_family_gap_years=2)

    def test_allows_family_repeat_after_gap(self):
        # maize (Poaceae) repeating with one different-family crop (soybean,
        # Fabaceae) between them is allowed under a 2-year gap rule.
        assert passes_agronomic_rules([MAIZE, SOYBEAN, MAIZE], min_family_gap_years=2)

    def test_rejects_same_family_within_gap(self):
        # maize (Poaceae) then rye (Poaceae) one year later violates a 2-year gap
        assert not passes_agronomic_rules([MAIZE, RYE_COVER], min_family_gap_years=2)


class TestSoilScore:
    def test_bounded_zero_to_one(self):
        for crop in (MAIZE, SOYBEAN, RYE_COVER, ALFALFA):
            score = soil_score(crop, None, baseline())
            assert 0.0 <= score <= 1.0

    def test_missing_soil_data_scores_neutral_not_worst_case(self):
        """Regression test for the bug found while preparing the pitch
        report: when soil_carbon_is_estimated is True, the fallback value
        must not be scored as if it were a real depleted-soil reading."""
        estimated = baseline(soil_organic_carbon_g_kg=15.0, soil_carbon_is_estimated=True)
        real_depleted = baseline(soil_organic_carbon_g_kg=15.0, soil_carbon_is_estimated=False)

        score_estimated = soil_score(MAIZE, None, estimated)
        score_real_depleted = soil_score(MAIZE, None, real_depleted)

        # Same numeric SOC value, but the estimated case should score higher
        # (neutral 0.5 carbon component) than the real-depleted case (0
        # carbon component), not identically.
        assert score_estimated > score_real_depleted

    def test_root_diversity_bonus_applied(self):
        same_depth_prev = {**SOYBEAN, "root_depth_class": MAIZE["root_depth_class"]}
        score_same_depth = soil_score(MAIZE, same_depth_prev, baseline())
        score_diff_depth = soil_score(MAIZE, ALFALFA, baseline())  # different root_depth_class
        assert score_diff_depth > score_same_depth


class TestWaterScore:
    def test_full_score_when_demand_covered(self):
        assert water_score(crop_water_demand_mm=100, baseline=baseline(seasonal_precip_mm=1000)) == 1.0

    def test_low_score_under_severe_deficit(self):
        dry = baseline(seasonal_precip_mm=10, mean_root_zone_wetness=0.0)
        assert water_score(crop_water_demand_mm=500, baseline=dry) < 0.2


class TestResilienceScore:
    @pytest.mark.parametrize("tolerance,expected", [("low", 0.2), ("medium", 0.6), ("high", 1.0)])
    def test_mapping(self, tolerance, expected):
        assert resilience_score({"drought_tolerance": tolerance}) == expected

    def test_unknown_tolerance_defaults_mid(self):
        assert resilience_score({"drought_tolerance": "unknown"}) == 0.5


class TestRevenueScore:
    def test_zero_for_no_market_revenue(self):
        assert revenue_score(RYE_COVER) == 0.0

    def test_positive_for_market_crop(self):
        assert 0.0 < revenue_score(MAIZE) <= 1.0

    def test_higher_yield_scores_higher(self):
        # maize (11 t/ha) should outscore soybean (3.4 t/ha)
        assert revenue_score(MAIZE) > revenue_score(SOYBEAN)


class TestErosionProtectionScore:
    def test_perennial_scores_highest(self):
        assert erosion_protection_score(ALFALFA) >= erosion_protection_score(MAIZE)

    def test_cover_crop_beats_row_crop(self):
        assert erosion_protection_score(RYE_COVER) > erosion_protection_score(SOYBEAN)


class TestBareFieldDays:
    def test_perennial_has_zero_bare_days(self):
        assert bare_field_days_in_year(ALFALFA) == 0

    def test_short_season_crop_has_more_bare_days(self):
        # oats (120-day season in this fixture set) should leave more bare
        # days than a longer-season crop like winter wheat-style cover.
        short_season = {"season_length_days": 120}
        long_season = {"season_length_days": 240}
        assert bare_field_days_in_year(short_season) > bare_field_days_in_year(long_season)

    def test_never_negative_for_full_year_season(self):
        assert bare_field_days_in_year({"season_length_days": 400}) == 0

    def test_impact_metrics_credit_lower_bare_days_than_baseline(self):
        # an alfalfa-containing rotation should show fewer cumulative bare
        # days than a continuous-maize baseline over the same length.
        metrics = compute_impact_metrics(
            sequence=[ALFALFA, MAIZE, ALFALFA],
            water_demands_mm=[300, 500, 300],
            baseline_crop=MAIZE,
            baseline_water_demand_mm=500,
        )
        assert metrics["bare_field_days_avoided"] > 0


class TestSingleYearPerennials:
    def test_flags_isolated_perennial(self):
        assert single_year_perennials([RYE_COVER, ALFALFA, RYE_COVER]) == ["alfalfa"]

    def test_does_not_flag_consecutive_perennial(self):
        assert single_year_perennials([RYE_COVER, ALFALFA, ALFALFA]) == []

    def test_no_perennial_in_sequence(self):
        assert single_year_perennials([MAIZE, SOYBEAN, RYE_COVER]) == []


class TestRisksAndGaps:
    def test_always_includes_four_standing_caveats(self):
        risks = generate_risks_and_gaps(frost_risk_crops=[], soil_is_estimated=False)
        assert len(risks) == 4

    def test_appends_climate_mismatch_note(self):
        mismatch = [{"crop": "maize", "site_mean_temp_c": 5.0, "crop_temp_tolerance_c": [10, 35]}]
        risks = generate_risks_and_gaps(
            frost_risk_crops=[], soil_is_estimated=False, climate_mismatched_crops=mismatch
        )
        assert any("maize" in r and "viable growing window" in r for r in risks)


class TestNewLegumes:
    """Regression tests for lentil/chickpea, added after crops.json was
    expanded for the frontend's crop-card set (see docs/data-science-approach.md)."""

    def test_bounded_zero_to_one(self):
        for crop in (LENTIL, CHICKPEA):
            assert 0.0 <= soil_score(crop, None, baseline()) <= 1.0
            assert 0.0 <= revenue_score(crop) <= 1.0

    def test_same_family_as_soybean_and_alfalfa_triggers_gap_rule(self):
        # lentil/chickpea are Fabaceae, same as soybean/alfalfa -- repeating
        # any of these back-to-back should be rejected just like soybean is.
        assert not passes_agronomic_rules([LENTIL, CHICKPEA], min_family_gap_years=2)
        assert not passes_agronomic_rules([CHICKPEA, SOYBEAN], min_family_gap_years=2)

    def test_allowed_after_a_non_legume_gap(self):
        assert passes_agronomic_rules([LENTIL, MAIZE, CHICKPEA], min_family_gap_years=2)

    def test_lower_yield_scores_lower_than_soybean(self):
        # both are low-yield pulses relative to the existing row crops
        assert revenue_score(LENTIL) < revenue_score(SOYBEAN)
        assert revenue_score(CHICKPEA) < revenue_score(SOYBEAN)


class TestRiceAndSorghum:
    """Regression tests for rice/sorghum, added to demonstrate the dataset
    can extend past the US-Midwest crop set (see docs/algorithm.md section
    13/15 on the global-coverage gap)."""

    def test_bounded_zero_to_one(self):
        for crop in (RICE, SORGHUM):
            assert 0.0 <= soil_score(crop, None, baseline()) <= 1.0
            assert 0.0 <= revenue_score(crop) <= 1.0

    def test_same_family_as_maize_triggers_gap_rule(self):
        # rice and sorghum are Poaceae, same as maize/wheat/oats/rye.
        assert not passes_agronomic_rules([RICE, MAIZE], min_family_gap_years=2)
        assert not passes_agronomic_rules([SORGHUM, MAIZE], min_family_gap_years=2)

    def test_sorghum_more_drought_resilient_than_rice(self):
        # sorghum's whole agronomic point is drought tolerance; rice is
        # flooded paddy and has essentially none.
        assert resilience_score(SORGHUM) > resilience_score(RICE)

    def test_rice_flags_flood_irrigation_water_accounting_gap(self):
        risks = generate_risks_and_gaps(
            frost_risk_crops=[], soil_is_estimated=False, flood_irrigated_crops=["rice"]
        )
        assert any("rice" in r and "percolation" in r for r in risks)

    def test_sorghum_does_not_flag_flood_irrigation_gap(self):
        risks = generate_risks_and_gaps(
            frost_risk_crops=[], soil_is_estimated=False, flood_irrigated_crops=[]
        )
        assert not any("percolation" in r for r in risks)


class TestRotationWeights:
    def test_normalizes_to_sum_one(self):
        w = RotationWeights(soil=1, water=1, resilience=1, revenue=1).normalized()
        assert w.soil + w.water + w.resilience + w.revenue == pytest.approx(1.0)

    def test_missing_key_falls_back_to_default(self):
        # RotationWeights(**{"soil": 1}) should not zero out the other weights
        w = RotationWeights(soil=1)
        assert w.water > 0 and w.resilience > 0 and w.revenue > 0
