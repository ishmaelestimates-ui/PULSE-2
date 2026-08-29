"""
Episode endpoints: create, fetch (with review statuses), and CSV export
of accepted markers for DaVinci Resolve.
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.models.editorial_review import DecisionType, EditorialReview, ReviewStatus
from app.models.episode import Episode
from app.schemas.episode import (
    EpisodeCreate,
    EpisodeDetailOut,
    EpisodeListItemOut,
    EpisodeOut,
)

router = APIRouter(prefix="/api/v1/episodes", tags=["episodes"])

# Resolve marker colors per decision type. DaVinci Resolve's marker CSV
# import accepts a fixed palette of color names.
_MARKER_COLOR_BY_TYPE = {
    DecisionType.STRONG_MOMENT: "Green",
    DecisionType.WEAK_SECTION: "Red",
    DecisionType.CLIP_CANDIDATE: "Blue",
    DecisionType.OPENING: "Yellow",
    DecisionType.CLOSING: "Yellow",
}

_MARKER_NAME_BY_TYPE = {
    DecisionType.STRONG_MOMENT: "Strong Moment",
    DecisionType.WEAK_SECTION: "Weak Section",
    DecisionType.CLIP_CANDIDATE: "Clip Candidate",
    DecisionType.OPENING: "Opening Candidate",
    DecisionType.CLOSING: "Closing Candidate",
}


def _seconds_to_timecode(total_seconds: float, frame_rate: float) -> str:
    """Convert a seconds offset into HH:MM:SS:FF timecode at the given
    (non-drop-frame) frame rate."""
    if total_seconds < 0:
        total_seconds = 0.0

    total_frames = round(total_seconds * frame_rate)
    frames_per_hour = round(frame_rate * 3600)
    frames_per_minute = round(frame_rate * 60)
    frame_rate_int = round(frame_rate)

    hours, remainder = divmod(total_frames, frames_per_hour)
    minutes, remainder = divmod(remainder, frames_per_minute)
    seconds, frames = divmod(remainder, frame_rate_int)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def _extract_span(review: EditorialReview) -> tuple[float, float]:
    """Return (start_seconds, end_seconds) for a review regardless of
    whether its decision_reference stores a point event (timestamp) or a
    range event (start/end)."""
    ref = review.decision_reference or {}
    if "start" in ref and "end" in ref:
        return float(ref["start"]), float(ref["end"])
    timestamp = float(ref.get("timestamp", 0.0))
    return timestamp, timestamp


def _extract_note(review: EditorialReview) -> str:
    ref = review.decision_reference or {}
    return str(
        ref.get("description") or ref.get("reason") or ref.get("hook") or ""
    )


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = (
        db.query(Episode)
        .options(selectinload(Episode.reviews))
        .filter(Episode.id == episode_id)
        .first()
    )
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found.",
        )
    return episode


def _derive_status(episode: Episode, media_count: int, review_counts: dict) -> str:
    """Best-effort lifecycle label for the episode list view. Purely
    derived from existing data — not stored."""
    total_reviews = sum(review_counts.values())
    if review_counts["accepted"] > 0 or review_counts["rejected"] > 0:
        return "reviewed"
    if total_reviews > 0 or episode.analysis:
        return "analyzed"
    if episode.transcript and episode.transcript.strip():
        return "transcribed"
    if media_count > 0:
        return "uploaded"
    return "draft"


@router.get("", response_model=list[EpisodeListItemOut])
def list_episodes(db: Session = Depends(get_db)):
    """List all episodes, newest first, with a derived lifecycle status
    (draft -> uploaded -> transcribed -> analyzed -> reviewed) and review
    counts for the list view."""
    episodes = (
        db.query(Episode)
        .options(selectinload(Episode.reviews), selectinload(Episode.media_files))
        .order_by(Episode.created_at.desc())
        .all()
    )

    items = []
    for episode in episodes:
        review_counts = {
            "recommended": sum(
                1 for r in episode.reviews if r.status == ReviewStatus.RECOMMENDED
            ),
            "accepted": sum(
                1 for r in episode.reviews if r.status == ReviewStatus.ACCEPTED
            ),
            "rejected": sum(
                1 for r in episode.reviews if r.status == ReviewStatus.REJECTED
            ),
        }
        media_count = len(episode.media_files)
        items.append(
            EpisodeListItemOut(
                id=episode.id,
                title=episode.title,
                duration=episode.duration,
                created_at=episode.created_at,
                status=_derive_status(episode, media_count, review_counts),
                media_count=media_count,
                recommended_count=review_counts["recommended"],
                accepted_count=review_counts["accepted"],
                rejected_count=review_counts["rejected"],
            )
        )
    return items


@router.post("", response_model=EpisodeOut, status_code=status.HTTP_201_CREATED)
def create_episode(payload: EpisodeCreate, db: Session = Depends(get_db)):
    """Create a new episode from a title, transcript, and optional
    duration. Analysis is triggered separately via the /analyze endpoint."""
    episode = Episode(
        title=payload.title,
        transcript=payload.transcript,
        duration=payload.duration,
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


@router.get("/{episode_id}", response_model=EpisodeDetailOut)
def get_episode(episode_id: int, db: Session = Depends(get_db)):
    """Fetch an episode along with its transcript, raw analysis payload,
    and every EditorialReview row (with current status) attached to it."""
    return _get_episode_or_404(db, episode_id)


@router.get("/{episode_id}/export/markers")
def export_markers(episode_id: int, db: Session = Depends(get_db)):
    """Export a CSV of ACCEPTED editorial decisions as DaVinci Resolve
    timeline markers: Start TC,End TC,Name,Note,Color."""
    episode = _get_episode_or_404(db, episode_id)
    settings = get_settings()
    frame_rate = settings.resolve_frame_rate

    accepted = [
        review for review in episode.reviews if review.status == ReviewStatus.ACCEPTED
    ]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Start TC", "End TC", "Name", "Note", "Color"])

    for review in sorted(accepted, key=lambda r: _extract_span(r)[0]):
        start_seconds, end_seconds = _extract_span(review)
        writer.writerow(
            [
                _seconds_to_timecode(start_seconds, frame_rate),
                _seconds_to_timecode(end_seconds, frame_rate),
                _MARKER_NAME_BY_TYPE.get(review.decision_type, "Marker"),
                _extract_note(review),
                _MARKER_COLOR_BY_TYPE.get(review.decision_type, "Green"),
            ]
        )

    buffer.seek(0)
    filename = f"episode_{episode_id}_markers.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
