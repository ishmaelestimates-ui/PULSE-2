"""
Pydantic schemas for the PR module (press kit, journalist leads,
embargoes, coverage).
"""
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.press import EmbargoStatus, JournalistLeadStatus


class PressKitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    episode_id: int
    press_release: str
    synopsis: dict[str, str]
    bios: list[dict[str, Any]]
    quotes: list[dict[str, Any]]
    faq: list[dict[str, Any]]
    contact_info: dict[str, Any]
    generated_at: datetime
    note: str = (
        "Bios are AI-drafted starting points meant to be edited by a "
        "human, not verified biographical facts. Quotes are pulled from "
        "this episode's own transcript."
    )


class JournalistMatchSuggestion(BaseModel):
    """Ephemeral — never persisted, never a named individual. See
    app/models/press.py module docstring."""

    outlet_type: str
    beat: str
    why_relevant: str
    search_tip: str


class JournalistMatchesResponse(BaseModel):
    episode_id: int
    suggestions: list[JournalistMatchSuggestion]
    note: str = (
        "These are AI-suggested outlet types and beats to research — not "
        "real named journalists or verified contact information. PULSE "
        "does not have a journalist database. Once you've found a real "
        "contact, add them with POST /journalist-leads to track outreach."
    )


class JournalistLeadCreate(BaseModel):
    name: Optional[str] = None
    outlet: Optional[str] = None
    beat: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class JournalistLeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    name: Optional[str]
    outlet: Optional[str]
    beat: Optional[str]
    email: Optional[str]
    notes: Optional[str]
    status: JournalistLeadStatus
    pitch_text: Optional[str]
    pitched_at: Optional[datetime]
    created_at: datetime


class SendPitchesRequest(BaseModel):
    journalist_lead_ids: list[int]


class SendPitchesResponse(BaseModel):
    episode_id: int
    results: list[JournalistLeadOut]
    note: str = (
        "No email was actually sent — PULSE has no email-sending "
        "integration configured. Pitch text was drafted and saved to "
        "each lead; send it yourself from your own email client."
    )


class EmbargoCreate(BaseModel):
    journalist_lead_id: Optional[int] = None
    embargo_date: date
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None


class EmbargoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    journalist_lead_id: Optional[int]
    embargo_date: date
    follow_up_date: Optional[date]
    status: EmbargoStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class CoverageCreate(BaseModel):
    outlet_name: str
    article_url: str
    title: str
    published_date: Optional[date] = None
    snippet: Optional[str] = None


class CoverageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    outlet_name: str
    article_url: str
    title: str
    published_date: Optional[date]
    snippet: Optional[str]
    created_at: datetime
