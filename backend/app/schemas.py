from pydantic import BaseModel


class FarmRequest(BaseModel):
    lat: float
    lon: float
    start_date: str = "20230101"  # YYYYMMDD, per NASA POWER's date format
    end_date: str = "20231231"
    priority_weights: dict[str, float] = {"soil": 0.4, "water": 0.4, "resilience": 0.2}
    sequence_length: int = 3
    top_n: int = 5


class RankedRotation(BaseModel):
    sequence: list[str]
    rsi: float
    year_breakdown: list[dict]


class FarmResponse(BaseModel):
    soil: dict
    mean_et0_mm_day: float
    top_rotations: list[RankedRotation]
