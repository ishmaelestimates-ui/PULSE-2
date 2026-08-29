"""
Pydantic schemas for film features.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.film import FestivalMatchStatus, TerritoryReleaseStatus


class FilmActOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    act_number: int
    title: str
    start_time: float
    end_time: float
    description: str
    confidence: float


class ActsResponse(BaseModel):
    episode_id: int
    acts: list[FilmActOut]
    note: str = "AI's read of the narrative arc — a starting point for editing, not ground truth."


class TrailerCutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    version: int
    clip_order: int
    start_time: float
    end_time: float
    description: str
    scene_type: str
    review_id: Optional[int]


class TrailerCutListResponse(BaseModel):
    episode_id: int
    cuts: dict[str, list[TrailerCutOut]]  # "30" / "60" / "90" -> clips
    note: str = (
        "Selection and ordering are deterministic (ranked by confidence + "
        "hype score, packed to fit each duration). scene_type is Gemini's "
        "qualitative read of tone, used only for marker coloring."
    )


class ExportTrailerRequest(BaseModel):
    version: int  # 30, 60, or 90


class FestivalMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    festival_name: str
    tier: int
    why_relevant: Optional[str]
    deadline: Optional[date]
    entry_fee: Optional[str]
    verified: bool
    status: FestivalMatchStatus
    notes: Optional[str]
    created_at: datetime


class FestivalMatchesResponse(BaseModel):
    episode_id: int
    matches: list[FestivalMatchOut]
    note: str = (
        "Festival names and tiers are reasonable suggestions, but deadlines "
        "and entry fees are AI-guessed and NOT verified — festival dates "
        "change every year and Gemini's training data goes stale. Treat "
        "every deadline here as 'check the festival's actual site' until "
        "you've marked it verified."
    )


class FestivalMatchUpdate(BaseModel):
    deadline: Optional[date] = None
    entry_fee: Optional[str] = None
    verified: Optional[bool] = None
    status: Optional[FestivalMatchStatus] = None
    notes: Optional[str] = None


class FestivalSubmissionResponse(BaseModel):
    episode_id: int
    logline: str
    synopsis: str
    directors_statement: str
    key_art_brief: str
    note: str = (
        "Ready to copy-paste and edit. 'Key art brief' is a written "
        "creative brief for a designer, not a generated image. Most "
        "festivals accept submissions through FilmFreeway or a similar "
        "platform — check the specific festival's own submission page for "
        "exact requirements and formats."
    )


class TerritoryReleaseCreate(BaseModel):
    territory: str
    release_date: date
    notes: Optional[str] = None


class TerritoryReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    territory: str
    release_date: date
    status: TerritoryReleaseStatus
    notes: Optional[str]


class TerritoryScheduleResponse(BaseModel):
    episode_id: int
    releases: list[TerritoryReleaseOut]
    note: str = (
        "Planning targets you set — not real distribution deals. PULSE "
        "has no distribution-partner integration."
    )


class SyncLicensingFlag(BaseModel):
    excerpt: str
    timestamp: Optional[float]
    concern_type: str  # "music_mention" | "third_party_content" | "other"
    recommended_action: str


class SyncLicensingReportResponse(BaseModel):
    episode_id: int
    flags: list[SyncLicensingFlag]
    note: str = (
        "NOT legal advice. This is a heuristic transcript scan for things "
        "worth a human (ideally a lawyer) reviewing — mentions of songs, "
        "artists, or other third-party content. It can miss real issues "
        "and can flag things that turn out to be fine. Do not treat an "
        "empty list as clearance."
    )
