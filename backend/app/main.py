"""FastAPI app wrapping the rotation scoring engine for the frontend.

Run from backend/: uvicorn app.main:app --reload
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.data.nasa_power import fetch_power_daily
from app.data.soilgrids import fetch_soilgrids
from app.engine.candidates import generate_candidate_sequences
from app.engine.climate_suitability import filter_climate_suitable_crops, frost_days_in_best_window
from app.engine.evapotranspiration import crop_water_demand_mm, et0_penman_monteith
from app.engine.rotation_scoring import (
    EnvironmentalBaseline,
    RotationWeights,
    compute_impact_metrics,
    generate_risks_and_gaps,
    score_sequence,
)
from app.schemas import FarmRequest, FarmResponse

CROPS_PATH = Path(__file__).resolve().parents[2] / "data" / "crops.json"

app = FastAPI(title="Field Shift Crop Rotation API")

# Open CORS for the hackathon demo; tighten if this ever goes beyond that.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/rotations", response_model=FarmResponse)
def rank_rotations(request: FarmRequest):
    crops = json.loads(CROPS_PATH.read_text())

    power_df = fetch_power_daily(request.lat, request.lon, start=request.start_date, end=request.end_date)
    soil = fetch_soilgrids(request.lat, request.lon)
    et0 = et0_penman_monteith(power_df, lat_deg=request.lat)

    baseline = EnvironmentalBaseline(
        seasonal_precip_mm=float(power_df["PRECTOTCORR"].sum()),
        mean_root_zone_wetness=float(power_df["GWETROOT"].mean()),
        soil_organic_carbon_g_kg=soil["soc_g_kg"] or 15.0,
    )

    weights = RotationWeights(**request.priority_weights)
    suitable_crops, excluded_crops = filter_climate_suitable_crops(crops, power_df)
    candidates = generate_candidate_sequences(suitable_crops, sequence_length=request.sequence_length)

    baseline_crop_name = crops.get("_baseline_crop", "maize")
    baseline_crop = {**crops[baseline_crop_name], "_name": baseline_crop_name}
    baseline_water_demand_mm = crop_water_demand_mm(et0, baseline_crop)
    soil_is_estimated = soil.get("soc_g_kg") is None

    def score_named_sequence(sequence: list[dict]) -> dict:
        water_demands = [crop_water_demand_mm(et0, crop) for crop in sequence]
        result = score_sequence(sequence, baseline, water_demands, weights)
        result["impact_metrics"] = compute_impact_metrics(
            sequence, water_demands, baseline_crop, baseline_water_demand_mm
        )
        frost_risk_crops = list(dict.fromkeys(
            crop["_name"] for crop in sequence if frost_days_in_best_window(power_df, crop) > 0
        ))
        result["risks_and_gaps"] = generate_risks_and_gaps(frost_risk_crops, soil_is_estimated)
        return result

    results = [score_named_sequence(sequence) for sequence in candidates]
    results.sort(key=lambda r: r["rsi"], reverse=True)

    current_rotation = None
    if request.current_rotation:
        unknown = [name for name in request.current_rotation if name not in crops]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown crop(s) in current_rotation: {unknown}")
        current_sequence = [{**crops[name], "_name": name} for name in request.current_rotation]
        current_rotation = score_named_sequence(current_sequence)

    return FarmResponse(
        soil=soil,
        mean_et0_mm_day=float(et0.mean()),
        top_rotations=results[: request.top_n],
        excluded_crops=excluded_crops,
        current_rotation=current_rotation,
    )
