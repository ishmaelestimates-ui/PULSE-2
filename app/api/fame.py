"""
Fame module endpoints. See app/models/fame.py and
app/services/fame_service.py for the honesty framing — the score is a
deterministic PULSE-internal index, mentions/sentiment are real (Reddit
search + real NLP), and competitor/cultural-footprint data is entirely
user-entered.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dashboard import ProjectMilestone
from app.models.editorial_review import EditorialReview, ReviewStatus
from app.models.episode import Episode
from app.models.fame import CompetitorBenchmark, CulturalFootprintItem, FameScoreSnapshot, Mention, MentionSentiment
from app.models.film import FestivalMatch
from app.models.press import Coverage
from app.models.reddit import RedditPost
from app.schemas.fame import (
    CompetitorBenchmarkCreate,
    CompetitorBenchmarkOut,
    CulturalFootprintCreate,
    CulturalFootprintOut,
    FameHistoryResponse,
    FameProjectionResponse,
    FameScoreOut,
    MentionCreate,
    MentionOut,
    MentionSearchResponse,
)
from app.services import fame_service, reddit_service

router = APIRouter(prefix="/api/v1/episodes", tags=["fame"])


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Episode {episode_id} not found.")
    return episode


@router.get("/{episode_id}/fame/score", response_model=FameScoreOut)
def get_fame_score(episode_id: int, db: Session = Depends(get_db)):
    """Computes fresh from real data every call. Stores at most one
    snapshot per calendar day (for history/projection), so repeated
    dashboard loads don't spam the history table."""
    _get_episode_or_404(db, episode_id)

    reddit_posts = db.query(RedditPost).filter(RedditPost.episode_id == episode_id).all()
    accepted_count = (
        db.query(EditorialReview)
        .filter(EditorialReview.episode_id == episode_id, EditorialReview.status == ReviewStatus.ACCEPTED)
        .count()
    )
    coverage_count = db.query(Coverage).filter(Coverage.episode_id == episode_id).count()
    festival_matches = db.query(FestivalMatch).filter(FestivalMatch.episode_id == episode_id).all()
    milestones_done = (
        db.query(ProjectMilestone)
        .filter(ProjectMilestone.episode_id == episode_id, ProjectMilestone.status == "done")
        .count()
    )

    previous = (
        db.query(FameScoreSnapshot)
        .filter(FameScoreSnapshot.episode_id == episode_id)
        .order_by(FameScoreSnapshot.recorded_at.desc())
        .first()
    )
    previous_raw_total = None
    if previous:
        c = previous.components
        previous_raw_total = c.get("engagement", 0) + c.get("reach_proxy", 0) + c.get("authority_proxy", 0)

    result = fame_service.compute_fame_score(
        reddit_posts, accepted_count, coverage_count, festival_matches, milestones_done, previous_raw_total
    )

    today = datetime.now(timezone.utc).date()
    existing_today = previous if previous and previous.recorded_at.date() == today else None
    if existing_today:
        existing_today.score = result["score"]
        existing_today.components = result["components"]
        snapshot = existing_today
    else:
        snapshot = FameScoreSnapshot(episode_id=episode_id, score=result["score"], components=result["components"])
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/{episode_id}/fame/history", response_model=FameHistoryResponse)
def get_fame_history(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    snapshots = (
        db.query(FameScoreSnapshot)
        .filter(FameScoreSnapshot.episode_id == episode_id)
        .order_by(FameScoreSnapshot.recorded_at)
        .all()
    )
    return FameHistoryResponse(episode_id=episode_id, snapshots=snapshots)


@router.get("/{episode_id}/fame/projection", response_model=FameProjectionResponse)
def get_fame_projection(
    episode_id: int, horizon_days: int = Query(30, description="30, 90, or 365"), db: Session = Depends(get_db)
):
    _get_episode_or_404(db, episode_id)
    snapshots = (
        db.query(FameScoreSnapshot)
        .filter(FameScoreSnapshot.episode_id == episode_id)
        .order_by(FameScoreSnapshot.recorded_at)
        .all()
    )
    if not snapshots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No fame score history yet — call GET .../fame/score at least "
                "once (twice, ideally on different days, for a real trend)."
            ),
        )

    first_date = snapshots[0].recorded_at.date()
    history = [((s.recorded_at.date() - first_date).days, s.score) for s in snapshots]
    result = fame_service.project_score(history, horizon_days)

    return FameProjectionResponse(episode_id=episode_id, horizon_days=horizon_days, **result)


@router.get("/{episode_id}/fame/mentions", response_model=list[MentionOut])
def list_mentions(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    return db.query(Mention).filter(Mention.episode_id == episode_id).order_by(Mention.found_at.desc()).all()


@router.get("/{episode_id}/fame/mentions/search-reddit", response_model=MentionSearchResponse)
def search_reddit_mentions(episode_id: int, q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Real Reddit search, saved as Mention rows with source='reddit'."""
    _get_episode_or_404(db, episode_id)
    raw_results = reddit_service.search_mentions(q)

    saved = []
    for r in raw_results:
        if r.get("url") and db.query(Mention).filter(Mention.episode_id == episode_id, Mention.url == r["url"]).first():
            continue
        mention = Mention(
            episode_id=episode_id,
            source="reddit",
            platform=r["platform"],
            url=r.get("url"),
            excerpt=r["excerpt"][:2000],
            author=r.get("author"),
        )
        db.add(mention)
        saved.append(mention)
    db.commit()
    for m in saved:
        db.refresh(m)

    all_for_query = db.query(Mention).filter(Mention.episode_id == episode_id, Mention.source == "reddit").all()
    return MentionSearchResponse(episode_id=episode_id, query=q, results=saved or all_for_query[:15])


@router.post("/{episode_id}/fame/mentions", response_model=MentionOut, status_code=status.HTTP_201_CREATED)
def add_mention(episode_id: int, payload: MentionCreate, db: Session = Depends(get_db)):
    """Manual entry for anything outside Reddit."""
    _get_episode_or_404(db, episode_id)
    mention = Mention(episode_id=episode_id, source="manual", **payload.model_dump())
    db.add(mention)
    db.commit()
    db.refresh(mention)
    return mention


@router.post("/{episode_id}/fame/mentions/{mention_id}/analyze-sentiment", response_model=MentionOut)
def analyze_mention_sentiment(episode_id: int, mention_id: int, db: Session = Depends(get_db)):
    mention = db.query(Mention).filter(Mention.id == mention_id, Mention.episode_id == episode_id).first()
    if mention is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mention not found.")

    sentiment_str = fame_service.classify_sentiment(mention.excerpt)
    mention.sentiment = MentionSentiment(sentiment_str)
    db.add(mention)
    db.commit()
    db.refresh(mention)
    return mention


@router.get("/{episode_id}/fame/competitors", response_model=list[CompetitorBenchmarkOut])
def list_competitors(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    return db.query(CompetitorBenchmark).filter(CompetitorBenchmark.episode_id == episode_id).all()


@router.post("/{episode_id}/fame/competitors", response_model=CompetitorBenchmarkOut, status_code=status.HTTP_201_CREATED)
def add_competitor(episode_id: int, payload: CompetitorBenchmarkCreate, db: Session = Depends(get_db)):
    """Entirely user-entered real numbers — PULSE does not fabricate
    statistics about named third parties."""
    _get_episode_or_404(db, episode_id)
    row = CompetitorBenchmark(episode_id=episode_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{episode_id}/fame/cultural-footprint", response_model=list[CulturalFootprintOut])
def list_cultural_footprint(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    return (
        db.query(CulturalFootprintItem)
        .filter(CulturalFootprintItem.episode_id == episode_id)
        .order_by(CulturalFootprintItem.created_at.desc())
        .all()
    )


@router.post(
    "/{episode_id}/fame/cultural-footprint", response_model=CulturalFootprintOut, status_code=status.HTTP_201_CREATED
)
def add_cultural_footprint_item(episode_id: int, payload: CulturalFootprintCreate, db: Session = Depends(get_db)):
    """Manual log of things you found yourself — not auto-detected."""
    _get_episode_or_404(db, episode_id)
    item_type = payload.item_type or "other"
    row = CulturalFootprintItem(
        episode_id=episode_id, item_type=item_type, description=payload.description, url=payload.url
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
