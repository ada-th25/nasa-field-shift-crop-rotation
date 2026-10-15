from pydantic import BaseModel


class FarmRequest(BaseModel):
    lat: float
    lon: float
    priority_weights: dict[str, float] = {"soil": 0.4, "water": 0.4, "resilience": 0.2}
    sequence_length: int = 3


class RankedRotation(BaseModel):
    sequence: list[str]
    rsi: float
    year_breakdown: list[dict]


class FarmResponse(BaseModel):
    soil: dict
    mean_et0_mm_day: float
    top_rotations: list[RankedRotation]
