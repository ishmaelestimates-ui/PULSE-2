"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.editorial_review import DecisionType, ReviewStatus


# ---------------------------------------------------------------------------
# Episode schemas
# ---------------------------------------------------------------------------
class EpisodeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    # Optional as of Night 2: episodes can be created "media-first" (upload
    # + transcribe later) instead of "transcript-first".
    transcript: Optional[str] = Field(default=None, min_length=1)
    duration: Optional[float] = Field(
        default=None, description="Episode duration in seconds"
    )


class EpisodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    duration: Optional[float]
    created_at: datetime


class EpisodeListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    duration: Optional[float]
    created_at: datetime
    status: str  # one of: draft, uploaded, transcribed, analyzed, reviewed
    media_count: int
    recommended_count: int
    accepted_count: int
    rejected_count: int


class EditorialReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    decision_type: DecisionType
    decision_reference: dict[str, Any]
    status: ReviewStatus
    updated_at: datetime


class EpisodeDetailOut(EpisodeOut):
    transcript: Optional[str] = None
    transcript_segments: Optional[list[dict[str, Any]]] = None
    analysis: Optional[dict[str, Any]] = None
    reviews: list[EditorialReviewOut] = []


# ---------------------------------------------------------------------------
# Review schemas
# ---------------------------------------------------------------------------
class ReviewUpdate(BaseModel):
    review_id: int
    status: ReviewStatus


# ---------------------------------------------------------------------------
# Analysis schemas (shape of what we expect back from Gemini, and what we
# return to the client after persisting EditorialReview rows)
# ---------------------------------------------------------------------------
class StrongMoment(BaseModel):
    timestamp: float
    description: str
    confidence: float = Field(ge=0.0, le=1.0)


class WeakSection(BaseModel):
    start: float
    end: float
    reason: str


class ClipCandidate(BaseModel):
    start: float
    end: float
    hook: str


class OpeningClosingCandidate(BaseModel):
    timestamp: float
    description: str


class AnalysisResult(BaseModel):
    """Normalized shape of a Gemini analysis response."""

    strong_moments: list[StrongMoment] = []
    weak_sections: list[WeakSection] = []
    clip_candidates: list[ClipCandidate] = []
    opening_candidate: Optional[OpeningClosingCandidate] = None
    closing_candidate: Optional[OpeningClosingCandidate] = None
