"""End-to-end demo: fetch NASA POWER + SoilGrids data for a test farm,
score all valid 3-year rotation candidates, and print the top 5 ranked by
Rotational Suitability Index (RSI).

Run from the backend/ directory: python scripts/demo.py
Or for a different site: python scripts/demo.py <lat> <lon> [start] [end]
"""
import json
import sys
from pathlib import Path

from app.data.nasa_power import fetch_power_daily
from app.data.soilgrids import fetch_soilgrids
from app.engine.candidates import generate_candidate_sequences
from app.engine.climate_suitability import (
    climate_mismatched_crops,
    filter_climate_suitable_crops,
    frost_days_in_best_window,
)
from app.engine.evapotranspiration import crop_water_demand_mm, et0_penman_monteith
from app.engine.rotation_scoring import (
    EnvironmentalBaseline,
    RotationWeights,
    compute_impact_metrics,
    generate_risks_and_gaps,
    score_sequence,
    single_year_perennials,
)

# Defaults to Central Iowa; override with CLI args to try another site.
FARM_LAT = float(sys.argv[1]) if len(sys.argv) > 1 else 42.0308
FARM_LON = float(sys.argv[2]) if len(sys.argv) > 2 else -93.6319
START_DATE = sys.argv[3] if len(sys.argv) > 3 else "20230101"
END_DATE = sys.argv[4] if len(sys.argv) > 4 else "20231231"
CROPS_PATH = Path(__file__).resolve().parents[2] / "data" / "crops.json"


def main():
    crops = json.loads(CROPS_PATH.read_text())

    print(f"Fetching NASA POWER data for ({FARM_LAT}, {FARM_LON})...")
    power_df = fetch_power_daily(FARM_LAT, FARM_LON, start=START_DATE, end=END_DATE)

    print("Fetching SoilGrids data...")
    soil = fetch_soilgrids(FARM_LAT, FARM_LON)
    print(f"  Soil: {soil}")

    et0 = et0_penman_monteith(power_df, lat_deg=FARM_LAT)
    print(f"  Mean ET0: {et0.mean():.2f} mm/day, annual total: {et0.sum():.0f} mm")

    soil_is_estimated = soil.get("soc_g_kg") is None
    baseline = EnvironmentalBaseline(
        seasonal_precip_mm=float(power_df["PRECTOTCORR"].sum()),
        mean_root_zone_wetness=float(power_df["GWETROOT"].mean()),
        soil_organic_carbon_g_kg=soil["soc_g_kg"] or 15.0,
        soil_carbon_is_estimated=soil_is_estimated,
    )
    print(f"  Baseline: {baseline}")

    suitable_crops, excluded_crops = filter_climate_suitable_crops(crops, power_df)
    if excluded_crops:
        print(f"\n{len(excluded_crops)} crop(s) excluded as climate-unsuitable for this site:")
        for e in excluded_crops:
            lo, hi = e["crop_temp_tolerance_c"]
            print(f"    {e['crop']}: site mean {e['site_mean_temp_c']}C, tolerance [{lo}, {hi}]C")

    candidates = generate_candidate_sequences(suitable_crops, sequence_length=3)
    print(f"\n{len(candidates)} candidate rotations pass agronomic rules.")

    baseline_crop_name = crops.get("_baseline_crop", "maize")
    baseline_crop = {**crops[baseline_crop_name], "_name": baseline_crop_name}
    baseline_water_demand_mm = crop_water_demand_mm(et0, baseline_crop)

    weights = RotationWeights(soil=0.3, water=0.3, resilience=0.15, revenue=0.25)

    def score_named_sequence(sequence, is_current=False):
        water_demands = [crop_water_demand_mm(et0, crop) for crop in sequence]
        result = score_sequence(sequence, baseline, water_demands, weights)
        result["impact_metrics"] = compute_impact_metrics(
            sequence, water_demands, baseline_crop, baseline_water_demand_mm
        )
        frost_risk_crops = list(dict.fromkeys(
            crop["_name"] for crop in sequence if frost_days_in_best_window(power_df, crop) > 0
        ))
        mismatched = climate_mismatched_crops(sequence, power_df) if is_current else []
        result["risks_and_gaps"] = generate_risks_and_gaps(
            frost_risk_crops, soil_is_estimated, single_year_perennials(sequence), mismatched
        )
        return result

    results = [score_named_sequence(sequence) for sequence in candidates]
    results.sort(key=lambda r: r["rsi"], reverse=True)

    print(f"\nExisting rotation (continuous {baseline_crop_name}) for comparison:")
    current = score_named_sequence([baseline_crop] * 3, is_current=True)
    print(f"  RSI {current['rsi']:.3f}  {' -> '.join(current['sequence'])}")
    for risk in current["risks_and_gaps"]:
        print(f"      risk/gap: {risk}")

    print(f"\nTop 5 rotations (vs. continuous {baseline_crop_name} baseline):")
    for r in results[:5]:
        impact = r["impact_metrics"]
        print(f"  RSI {r['rsi']:.3f}  {' -> '.join(r['sequence'])}")
        print(
            f"      water saved: {impact['water_saved_mm']:.0f} mm ({impact['water_saved_pct']:.0f}%), "
            f"N fertilizer avoided: {impact['nitrogen_fertilizer_avoided_kg_ha']:.0f} kg/ha, "
            f"SDGs: {', '.join(t['sdg'] for t in impact['sdg_tags']) or 'none'}"
        )
        for risk in r["risks_and_gaps"]:
            print(f"      risk/gap: {risk}")


if __name__ == "__main__":
    main()
