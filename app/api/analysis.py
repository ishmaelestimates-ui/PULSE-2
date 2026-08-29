"""
Analysis endpoint: runs Gemini over an episode's transcript and persists
the results both as a raw JSON blob (Episode.analysis) and as normalized,
individually reviewable EditorialReview rows.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.editorial_review import DecisionType, EditorialReview, ReviewStatus
from app.models.episode import Episode
from app.schemas.episode import AnalysisResult, EpisodeDetailOut
from app.services.gemini_service import GeminiService, get_gemini_service

router = APIRouter(prefix="/api/v1/episodes", tags=["analysis"])


def _persist_analysis(db: Session, episode: Episode, result: AnalysisResult) -> None:
    """Replace any existing EditorialReview rows for this episode with a
    fresh set derived from `result`, and store the raw payload on the
    episode itself."""
    # Clear prior recommendations for this episode before writing new
    # ones, so re-running analysis doesn't accumulate duplicates.
    db.query(EditorialReview).filter(
        EditorialReview.episode_id == episode.id
    ).delete()

    for moment in result.strong_moments:
        db.add(
            EditorialReview(
                episode_id=episode.id,
                decision_type=DecisionType.STRONG_MOMENT,
                decision_reference=moment.model_dump(),
                status=ReviewStatus.RECOMMENDED,
            )
        )

    for section in result.weak_sections:
        db.add(
            EditorialReview(
                episode_id=episode.id,
                decision_type=DecisionType.WEAK_SECTION,
                decision_reference=section.model_dump(),
                status=ReviewStatus.RECOMMENDED,
            )
        )

    for clip in result.clip_candidates:
        db.add(
            EditorialReview(
                episode_id=episode.id,
                decision_type=DecisionType.CLIP_CANDIDATE,
                decision_reference=clip.model_dump(),
                status=ReviewStatus.RECOMMENDED,
            )
        )

    if result.opening_candidate is not None:
        db.add(
            EditorialReview(
                episode_id=episode.id,
                decision_type=DecisionType.OPENING,
                decision_reference=result.opening_candidate.model_dump(),
                status=ReviewStatus.RECOMMENDED,
            )
        )

    if result.closing_candidate is not None:
        db.add(
            EditorialReview(
                episode_id=episode.id,
                decision_type=DecisionType.CLOSING,
                decision_reference=result.closing_candidate.model_dump(),
                status=ReviewStatus.RECOMMENDED,
            )
        )

    episode.analysis = result.model_dump()
    db.add(episode)
    db.commit()
    db.refresh(episode)


@router.post("/{episode_id}/analyze", response_model=EpisodeDetailOut)
def analyze_episode(
    episode_id: int,
    db: Session = Depends(get_db),
    gemini: GeminiService = Depends(get_gemini_service),
):
    """Run Gemini analysis on the episode's transcript, then persist the
    results as EditorialReview rows (status=recommended) plus the raw
    analysis JSON on the episode."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found.",
        )

    if not episode.transcript or not episode.transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Episode has no transcript to analyze. Upload media and "
                "run POST /api/v1/episodes/{id}/transcribe first, or "
                "supply a transcript directly."
            ),
        )

    result = gemini.analyze_transcript(episode.transcript)
    _persist_analysis(db, episode, result)
    return episode
