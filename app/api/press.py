"""
PR module endpoints: press kit generation, journalist lead tracking
(not AI-generated contacts — see app/models/press.py), embargoes, and
manually-tracked coverage.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.editorial_review import EditorialReview, ReviewStatus
from app.models.episode import Episode
from app.models.press import Coverage, Embargo, JournalistLead, JournalistLeadStatus, PressKit
from app.schemas.press import (
    CoverageCreate,
    CoverageOut,
    EmbargoCreate,
    EmbargoOut,
    JournalistLeadCreate,
    JournalistLeadOut,
    JournalistMatchesResponse,
    PressKitOut,
    SendPitchesRequest,
    SendPitchesResponse,
)
from app.services import press_service

router = APIRouter(prefix="/api/v1/episodes", tags=["pr"])


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Episode {episode_id} not found.")
    return episode


@router.post("/{episode_id}/generate-press-kit", response_model=PressKitOut)
def generate_press_kit(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    if not episode.transcript or not episode.transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Episode has no transcript yet — transcribe it before generating a press kit.",
        )

    content = press_service.generate_press_kit_content(episode.title, episode.transcript)

    accepted_strong_moments = (
        db.query(EditorialReview)
        .filter(
            EditorialReview.episode_id == episode_id,
            EditorialReview.status == ReviewStatus.ACCEPTED,
            EditorialReview.decision_type == "strong_moment",
        )
        .all()
    )
    quotes = press_service.extract_quotes(episode.transcript_segments or [], accepted_strong_moments)

    kit = db.query(PressKit).filter(PressKit.episode_id == episode_id).first()
    if kit is None:
        kit = PressKit(episode_id=episode_id)

    try:
        kit.press_release = content["press_release"]
        kit.synopsis = {
            "100": content["synopsis_100"],
            "250": content["synopsis_250"],
            "500": content["synopsis_500"],
        }
        kit.bios = content["bios"]
        kit.faq = content["faq"]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini response was missing an expected field: {exc}"
        ) from exc

    kit.quotes = quotes
    kit.contact_info = kit.contact_info or {}

    db.add(kit)
    db.commit()
    db.refresh(kit)
    return kit


@router.get("/{episode_id}/journalist-matches", response_model=JournalistMatchesResponse)
def journalist_matches(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    suggestions = press_service.generate_journalist_suggestions(episode.title, episode.transcript or "")
    return JournalistMatchesResponse(episode_id=episode_id, suggestions=suggestions)


@router.get("/{episode_id}/journalist-leads", response_model=list[JournalistLeadOut])
def list_journalist_leads(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    return (
        db.query(JournalistLead)
        .filter(JournalistLead.episode_id == episode_id)
        .order_by(JournalistLead.created_at.desc())
        .all()
    )


@router.post("/{episode_id}/journalist-leads", response_model=JournalistLeadOut, status_code=status.HTTP_201_CREATED)
def create_journalist_lead(episode_id: int, payload: JournalistLeadCreate, db: Session = Depends(get_db)):
    """User-entered tracking record — see app/models/press.py."""
    _get_episode_or_404(db, episode_id)
    lead = JournalistLead(episode_id=episode_id, **payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{episode_id}/send-pitches", response_model=SendPitchesResponse)
def send_pitches(episode_id: int, payload: SendPitchesRequest, db: Session = Depends(get_db)):
    """Drafts a personalized pitch per lead and marks them as pitched.
    Does NOT actually send email — see SendPitchesResponse.note."""
    episode = _get_episode_or_404(db, episode_id)
    kit = db.query(PressKit).filter(PressKit.episode_id == episode_id).first()
    if kit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generate a press kit first (POST .../generate-press-kit) — pitches are drafted from it.",
        )

    leads = (
        db.query(JournalistLead)
        .filter(JournalistLead.episode_id == episode_id, JournalistLead.id.in_(payload.journalist_lead_ids))
        .all()
    )
    if not leads:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching journalist leads found.")

    for lead in leads:
        lead.pitch_text = press_service.draft_pitch(kit.press_release, lead.outlet, lead.beat, lead.notes)
        lead.status = JournalistLeadStatus.PITCHED
        lead.pitched_at = datetime.now(timezone.utc)
        db.add(lead)

    db.commit()
    for lead in leads:
        db.refresh(lead)
    return SendPitchesResponse(episode_id=episode_id, results=leads)


@router.get("/{episode_id}/embargoes", response_model=list[EmbargoOut])
def list_embargoes(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    return db.query(Embargo).filter(Embargo.episode_id == episode_id).order_by(Embargo.embargo_date).all()


@router.post("/{episode_id}/embargoes", response_model=EmbargoOut, status_code=status.HTTP_201_CREATED)
def create_embargo(episode_id: int, payload: EmbargoCreate, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    embargo = Embargo(episode_id=episode_id, **payload.model_dump())
    db.add(embargo)
    db.commit()
    db.refresh(embargo)
    return embargo


@router.get("/{episode_id}/coverage", response_model=list[CoverageOut])
def list_coverage(episode_id: int, db: Session = Depends(get_db)):
    """Manually-entered coverage only. No web scraping is implemented —
    building a reliable, ToS-compliant scraper/crawler per outlet is a
    substantial project on its own and easy to get wrong (rate limits,
    paywalls, structured-data variance); this returns what's been added
    by hand via POST below."""
    _get_episode_or_404(db, episode_id)
    return (
        db.query(Coverage)
        .filter(Coverage.episode_id == episode_id)
        .order_by(Coverage.published_date.desc().nullslast())
        .all()
    )


@router.post("/{episode_id}/coverage", response_model=CoverageOut, status_code=status.HTTP_201_CREATED)
def add_coverage(episode_id: int, payload: CoverageCreate, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    item = Coverage(episode_id=episode_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
