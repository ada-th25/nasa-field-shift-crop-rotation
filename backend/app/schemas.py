from pydantic import BaseModel


class FarmRequest(BaseModel):
    lat: float
    lon: float
    start_date: str = "20230101"  # YYYYMMDD, per NASA POWER's date format
    end_date: str = "20231231"
    priority_weights: dict[str, float] = {"soil": 0.3, "water": 0.3, "resilience": 0.15, "revenue": 0.25}
    sequence_length: int = 3
    top_n: int = 5
    current_rotation: list[str] | None = None
    """Optional: the farmer's actual current rotation (crop names from
    crops.json, e.g. ["maize"] for continuous maize, or a multi-year
    sequence). When given, it's scored through the same pipeline and
    returned as `current_rotation` so the UI can show it side by side with
    the recommended rotations, not just imply it via impact_metrics."""


class RankedRotation(BaseModel):
    sequence: list[str]
    rsi: float
    year_breakdown: list[dict]
    impact_metrics: dict
    risks_and_gaps: list[str] = []


class FarmResponse(BaseModel):
    soil: dict
    mean_et0_mm_day: float
    top_rotations: list[RankedRotation]
    excluded_crops: list[dict] = []
    current_rotation: RankedRotation | None = None
