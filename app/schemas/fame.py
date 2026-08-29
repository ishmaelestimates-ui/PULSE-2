"""
Pydantic schemas for the Fame module.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.fame import CulturalFootprintType, MentionSentiment


class FameScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    score: float
    components: dict[str, float]
    recorded_at: datetime
    note: str = (
        "An internal engagement index computed from PULSE's own tracked "
        "data — not a measurement of real-world fame, reach, or authority."
    )


class FameHistoryResponse(BaseModel):
    episode_id: int
    snapshots: list[FameScoreOut]


class FameProjectionResponse(BaseModel):
    episode_id: int
    horizon_days: int
    projected_score: float
    confidence: str  # "insufficient_history" | "naive_linear_trend"
    note: str = (
        "A mechanical linear extrapolation of PULSE's own internal index over "
        "time — not a real-world forecast of anyone's future fame."
    )


class MentionCreate(BaseModel):
    platform: str
    excerpt: str
    url: Optional[str] = None
    author: Optional[str] = None


class MentionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    source: str
    platform: str
    url: Optional[str]
    excerpt: str
    author: Optional[str]
    sentiment: MentionSentiment
    found_at: datetime


class MentionSearchResponse(BaseModel):
    episode_id: int
    query: str
    results: list[MentionOut]
    note: str = "Real Reddit search results. No other platform is automatically monitored — add those manually."


class CompetitorBenchmarkCreate(BaseModel):
    competitor_name: str
    metric_name: str
    competitor_value: float
    our_value: Optional[float] = None
    notes: Optional[str] = None


class CompetitorBenchmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    competitor_name: str
    metric_name: str
    competitor_value: float
    our_value: Optional[float]
    notes: Optional[str]
    created_at: datetime


class CulturalFootprintCreate(BaseModel):
    item_type: Optional[CulturalFootprintType] = None  # auto-classified if omitted
    description: str
    url: Optional[str] = None


class CulturalFootprintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    item_type: CulturalFootprintType
    description: str
    url: Optional[str]
    created_at: datetime
