"""End-to-end demo: fetch NASA POWER + SoilGrids data for a test farm near
Ames, Iowa, score all valid 3-year rotation candidates, and print the
top 5 ranked by Rotational Suitability Index (RSI).

Run from the backend/ directory: python scripts/demo.py
"""
import json
from pathlib import Path

from app.data.nasa_power import fetch_power_daily
from app.data.soilgrids import fetch_soilgrids
from app.engine.candidates import generate_candidate_sequences
from app.engine.evapotranspiration import crop_water_demand_mm, et0_penman_monteith
from app.engine.rotation_scoring import EnvironmentalBaseline, RotationWeights, score_sequence

# Central Iowa test farm
FARM_LAT = 42.0308
FARM_LON = -93.6319
CROPS_PATH = Path(__file__).resolve().parents[2] / "data" / "crops.json"


def main():
    crops = json.loads(CROPS_PATH.read_text())

    print(f"Fetching NASA POWER data for ({FARM_LAT}, {FARM_LON})...")
    power_df = fetch_power_daily(FARM_LAT, FARM_LON, start="20230101", end="20231231")

    print("Fetching SoilGrids data...")
    soil = fetch_soilgrids(FARM_LAT, FARM_LON)
    print(f"  Soil: {soil}")

    et0 = et0_penman_monteith(power_df, lat_deg=FARM_LAT)
    print(f"  Mean ET0: {et0.mean():.2f} mm/day, annual total: {et0.sum():.0f} mm")

    baseline = EnvironmentalBaseline(
        seasonal_precip_mm=float(power_df["PRECTOTCORR"].sum()),
        mean_root_zone_wetness=float(power_df["GWETROOT"].mean()),
        soil_organic_carbon_g_kg=soil["soc_g_kg"] or 15.0,
    )
    print(f"  Baseline: {baseline}")

    candidates = generate_candidate_sequences(crops, sequence_length=3)
    print(f"\n{len(candidates)} candidate rotations pass agronomic rules.")

    weights = RotationWeights(soil=0.4, water=0.4, resilience=0.2)
    results = []
    for sequence in candidates:
        water_demands = [crop_water_demand_mm(et0, crop) for crop in sequence]
        results.append(score_sequence(sequence, baseline, water_demands, weights))

    results.sort(key=lambda r: r["rsi"], reverse=True)

    print("\nTop 5 rotations:")
    for r in results[:5]:
        print(f"  RSI {r['rsi']:.3f}  {' -> '.join(r['sequence'])}")


if __name__ == "__main__":
    main()
