from datetime import date, timedelta

from pydantic import BaseModel, Field

# NASA POWER's most recent days are typically missing when queried (observed
# lag: ~3 days for temperature/soil wetness, ~5 days for solar radiation --
# see docs/algorithm.md). Defaulting to "today" would silently hand the
# climate-suitability filter and ET0 calc a tail of NaNs, so the default
# window instead ends a week back from whenever the request is made, and
# spans a full year before that so the climate filter has enough data to
# find a viable growing window regardless of hemisphere.
POWER_REPORTING_LAG_DAYS = 7


def _default_end_date() -> str:
    return (date.today() - timedelta(days=POWER_REPORTING_LAG_DAYS)).strftime("%Y%m%d")


def _default_start_date() -> str:
    return (date.today() - timedelta(days=POWER_REPORTING_LAG_DAYS + 365)).strftime("%Y%m%d")


class FarmRequest(BaseModel):
    lat: float
    lon: float
    start_date: str = Field(default_factory=_default_start_date)  # YYYYMMDD, per NASA POWER's date format
    end_date: str = Field(default_factory=_default_end_date)
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
