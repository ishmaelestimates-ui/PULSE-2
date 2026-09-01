"""
Pydantic schemas for the campaign / marketing pack.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class SocialPost(BaseModel):
    text: str
    hashtags: list[str] = []


class Hook(BaseModel):
    review_id: Optional[int] = None
    text: str
    curiosity_gap_score: int  # 1-10, Gemini's own self-rating


class Newsletter(BaseModel):
    subject: str
    preview: str
    body: str


class TrailerCutlistItem(BaseModel):
    review_id: Optional[int] = None
    start: float
    end: float
    label: str


class HypeScoreItem(BaseModel):
    review_id: int
    score: int  # 1-100, AI estimate — see campaign_service docstring
    rationale: str


class ViralPredictionItem(BaseModel):
    review_id: int
    platform: str
    label: str  # "viral" | "high" | "moderate" | "low"
    rationale: str


class CampaignPackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    episode_id: int
    social_posts: dict[str, SocialPost]
    hooks: list[Hook]
    schedule: dict[str, Any]
    press_blurb: str
    newsletter: Newsletter
    show_notes: str
    trailer_cutlist: list[TrailerCutlistItem]
    hype_scores: list[HypeScoreItem]
    viral_predictions: list[ViralPredictionItem]
    generated_at: datetime
    disclaimer: str = (
        "Hype scores and viral predictions are Gemini's qualitative read of "
        "the content (confidence, sentiment, hook strength) — not measured "
        "engagement data or a validated predictive model. Treat them as a "
        "second opinion, not a forecast."
    )


class HypeScoreResponse(BaseModel):
    episode_id: int
    scores: list[HypeScoreItem]
    disclaimer: str = CampaignPackOut.model_fields["disclaimer"].default


class ViralPredictionResponse(BaseModel):
    episode_id: int
    predictions: list[ViralPredictionItem]
    disclaimer: str = CampaignPackOut.model_fields["disclaimer"].default
