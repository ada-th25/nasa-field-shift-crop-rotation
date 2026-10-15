"""FastAPI app wrapping the rotation scoring engine for the frontend.

Run from backend/: uvicorn app.main:app --reload
"""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.data.nasa_power import fetch_power_daily
from app.data.soilgrids import fetch_soilgrids
from app.engine.candidates import generate_candidate_sequences
from app.engine.evapotranspiration import crop_water_demand_mm, et0_penman_monteith
from app.engine.rotation_scoring import EnvironmentalBaseline, RotationWeights, score_sequence
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

    power_df = fetch_power_daily(request.lat, request.lon, start="20230101", end="20231231")
    soil = fetch_soilgrids(request.lat, request.lon)
    et0 = et0_penman_monteith(power_df, lat_deg=request.lat)

    baseline = EnvironmentalBaseline(
        seasonal_precip_mm=float(power_df["PRECTOTCORR"].sum()),
        mean_root_zone_wetness=float(power_df["GWETROOT"].mean()),
        soil_organic_carbon_g_kg=soil["soc_g_kg"] or 15.0,
    )

    weights = RotationWeights(**request.priority_weights)
    candidates = generate_candidate_sequences(crops, sequence_length=request.sequence_length)

    results = []
    for sequence in candidates:
        water_demands = [crop_water_demand_mm(et0, crop) for crop in sequence]
        results.append(score_sequence(sequence, baseline, water_demands, weights))
    results.sort(key=lambda r: r["rsi"], reverse=True)

    return FarmResponse(
        soil=soil,
        mean_et0_mm_day=float(et0.mean()),
        top_rotations=results[:5],
    )
