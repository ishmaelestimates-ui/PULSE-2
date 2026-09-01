"""
Campaign / marketing pack endpoints.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campaign import CampaignPack
from app.models.editorial_review import EditorialReview, ReviewStatus
from app.models.episode import Episode
from app.schemas.campaign import CampaignPackOut, HypeScoreResponse, ViralPredictionResponse
from app.services import campaign_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/episodes", tags=["campaign"])


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found.",
        )
    return episode


def _get_campaign_or_404(db: Session, episode_id: int) -> CampaignPack:
    pack = db.query(CampaignPack).filter(CampaignPack.episode_id == episode_id).first()
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No campaign generated yet for episode {episode_id}. "
                "Run POST /api/v1/episodes/{episode_id}/generate-campaign first."
            ),
        )
    return pack


def _valid_review_ids(accepted_reviews: list) -> set[int]:
    return {r.id for r in accepted_reviews}


@router.post("/{episode_id}/generate-campaign", response_model=CampaignPackOut)
def generate_campaign(episode_id: int, db: Session = Depends(get_db)):
    """Generate (or regenerate) the full campaign pack: Gemini-written
    social posts/hooks/press blurb/newsletter/show notes, plus a
    deterministic release schedule and trailer cut list, plus AI-
    estimated hype scores and viral predictions. Requires at least one
    accepted strong moment or clip candidate."""
    episode = _get_episode_or_404(db, episode_id)

    accepted_reviews = (
        db.query(EditorialReview)
        .filter(
            EditorialReview.episode_id == episode_id,
            EditorialReview.status == ReviewStatus.ACCEPTED,
        )
        .all()
    )
    accepted_content = [
        r for r in accepted_reviews if r.decision_type in ("strong_moment", "clip_candidate")
    ]
    if not accepted_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No accepted strong moments or clip candidates yet. Run "
                "analysis and accept at least one recommendation in the "
                "Review tab before generating a campaign."
            ),
        )

    raw = campaign_service.generate_campaign_content(
        episode.title, episode.transcript or "", accepted_reviews
    )

    valid_ids = _valid_review_ids(accepted_reviews)

    # Defensive validation: an LLM can hallucinate review_id references.
    # Drop (don't crash on) anything that doesn't match a real accepted
    # review for this episode.
    hooks = [
        h for h in raw.get("hooks", []) if h.get("review_id") is None or h["review_id"] in valid_ids
    ]
    hype_scores = [
        h for h in raw.get("hype_scores", []) if h.get("review_id") in valid_ids
    ]
    viral_predictions = [
        v for v in raw.get("viral_predictions", []) if v.get("review_id") in valid_ids
    ]

    schedule = campaign_service.build_schedule()
    trailer_cutlist = campaign_service.build_trailer_cutlist(accepted_reviews)

    pack = db.query(CampaignPack).filter(CampaignPack.episode_id == episode_id).first()
    if pack is None:
        pack = CampaignPack(episode_id=episode_id)

    try:
        pack.social_posts = raw["social_posts"]
        pack.newsletter = raw["newsletter"]
        pack.press_blurb = raw["press_blurb"]
        pack.show_notes = raw["show_notes"]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini response was missing an expected field: {exc}",
        ) from exc

    pack.hooks = hooks
    pack.hype_scores = hype_scores
    pack.viral_predictions = viral_predictions
    pack.schedule = schedule
    pack.trailer_cutlist = trailer_cutlist

    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack


@router.get("/{episode_id}/campaign", response_model=CampaignPackOut)
def get_campaign(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    return _get_campaign_or_404(db, episode_id)


@router.get("/{episode_id}/hype-score", response_model=HypeScoreResponse)
def get_hype_scores(episode_id: int, db: Session = Depends(get_db)):
    """Reads hype scores from the most recently generated campaign pack
    rather than recomputing on every call — they're produced alongside
    the rest of the campaign copy in one Gemini call. Regenerate the
    campaign to refresh them."""
    _get_episode_or_404(db, episode_id)
    pack = _get_campaign_or_404(db, episode_id)
    return HypeScoreResponse(episode_id=episode_id, scores=pack.hype_scores)


@router.get("/{episode_id}/viral-prediction", response_model=ViralPredictionResponse)
def get_viral_predictions(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    pack = _get_campaign_or_404(db, episode_id)
    return ViralPredictionResponse(episode_id=episode_id, predictions=pack.viral_predictions)
