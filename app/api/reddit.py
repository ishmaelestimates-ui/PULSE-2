"""
Reddit distribution endpoints. See app/models/reddit.py and
app/services/reddit_service.py for the framing — this deliberately does
not implement "post as organic discussion, no self-promotion" tooling.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.episode import Episode
from app.models.reddit import RedditKarma, RedditPost, RedditPostStatus
from app.schemas.reddit import (
    RedditCommentSuggestRequest,
    RedditCommentSuggestResponse,
    RedditGenerateResponse,
    RedditKarmaEntry,
    RedditKarmaOut,
    RedditPostCreate,
    RedditPostOut,
    RedditScheduleRequest,
    RedditCommunityDNAOut,
    RedditIntelligenceResponse,
    RedditMovementRequest,
    SubredditAnalysis,
    SubredditSearchResponse,
)
from app.services import postiz_service, reddit_service

router = APIRouter(prefix="/api/v1", tags=["reddit"])


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Episode {episode_id} not found.")
    return episode


@router.get("/reddit/subreddits/search", response_model=SubredditSearchResponse)
def search_subreddits(q: str = Query(..., min_length=1)):
    results = reddit_service.search_subreddits(q)
    return SubredditSearchResponse(query=q, results=results)


@router.get("/reddit/subreddits/analyze/{subreddit}", response_model=SubredditAnalysis)
def analyze_subreddit(subreddit: str):
    data = reddit_service.analyze_subreddit(subreddit)
    return SubredditAnalysis(**data)


@router.post("/episodes/{episode_id}/reddit/generate", response_model=RedditGenerateResponse)
def generate_reddit_content(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    if not episode.transcript or not episode.transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Episode has no transcript yet — transcribe it before generating Reddit posts.",
        )

    content = reddit_service.generate_reddit_post_content(episode.title, episode.transcript)
    try:
        title_options = content["title_options"]
        body = content["body"]
        flair_suggestions = content["flair_suggestions"]
        keywords = content.get("topic_keywords", [])
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini response was missing an expected field: {exc}"
        ) from exc

    recommended = reddit_service.recommend_subreddits(keywords)

    return RedditGenerateResponse(
        episode_id=episode_id,
        title_options=title_options,
        body=body,
        flair_suggestions=flair_suggestions,
        recommended_subreddits=recommended,
        disclosure_note=reddit_service.DISCLOSURE_NOTE,
    )


@router.get("/episodes/{episode_id}/reddit/posts", response_model=list[RedditPostOut])
def list_reddit_posts(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    return db.query(RedditPost).filter(RedditPost.episode_id == episode_id).order_by(RedditPost.created_at.desc()).all()


@router.post("/episodes/{episode_id}/reddit/posts", response_model=RedditPostOut, status_code=status.HTTP_201_CREATED)
def create_reddit_post(episode_id: int, payload: RedditPostCreate, db: Session = Depends(get_db)):
    """Save a chosen title/body/subreddit (from /reddit/generate, edited
    or not) as a draft. disclosure_note is always set server-side."""
    _get_episode_or_404(db, episode_id)
    post = RedditPost(
        episode_id=episode_id,
        disclosure_note=reddit_service.DISCLOSURE_NOTE,
        **payload.model_dump(),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/episodes/{episode_id}/reddit/schedule", response_model=RedditPostOut)
def schedule_reddit_post(episode_id: int, payload: RedditScheduleRequest, db: Session = Depends(get_db)):
    """Schedules via Postiz. See app/services/postiz_service.py for the
    caveat on Reddit's exact per-platform settings schema."""
    _get_episode_or_404(db, episode_id)
    post = (
        db.query(RedditPost)
        .filter(RedditPost.id == payload.reddit_post_id, RedditPost.episode_id == episode_id)
        .first()
    )
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reddit post draft not found.")

    content_text = f"{post.title}\n\n{post.body}\n\n---\n{post.disclosure_note}"
    post_type = "schedule" if payload.scheduled_time else "now"
    scheduled_iso = payload.scheduled_time.isoformat() if payload.scheduled_time else None

    result = postiz_service.create_post(
        payload.postiz_integration_id, content_text, post_type=post_type, scheduled_iso=scheduled_iso
    )

    post.status = RedditPostStatus.SCHEDULED
    post.scheduled_time = payload.scheduled_time
    post.postiz_post_id = str(result.get("id")) if isinstance(result, dict) and result.get("id") else None
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/episodes/{episode_id}/reddit/performance", response_model=list[RedditPostOut])
def reddit_performance(episode_id: int, db: Session = Depends(get_db)):
    """Refreshes upvotes/comments from Postiz where possible (best-effort
    — see postiz_service.get_post_status), then returns stored values."""
    _get_episode_or_404(db, episode_id)
    posts = db.query(RedditPost).filter(RedditPost.episode_id == episode_id).all()

    for post in posts:
        if not post.postiz_post_id:
            continue
        status_data = postiz_service.get_post_status(post.postiz_post_id)
        metrics = status_data.get("metrics") or status_data.get("engagement") or {}
        if metrics:
            post.upvotes = metrics.get("upvotes", post.upvotes)
            post.comment_count = metrics.get("comments", post.comment_count)
            post.last_checked_at = datetime.now(timezone.utc)
            db.add(post)

    db.commit()
    return posts


@router.post("/reddit/comment/suggest", response_model=RedditCommentSuggestResponse)
def suggest_comment_reply(payload: RedditCommentSuggestRequest):
    reply = reddit_service.suggest_comment_reply(payload.comment_body, payload.episode_context)
    return RedditCommentSuggestResponse(comment_body=payload.comment_body, suggested_reply=reply)


@router.get("/reddit/karma", response_model=list[RedditKarmaOut])
def get_karma_history(db: Session = Depends(get_db)):
    return db.query(RedditKarma).order_by(RedditKarma.recorded_at).all()


@router.post("/reddit/karma", response_model=RedditKarmaOut, status_code=status.HTTP_201_CREATED)
def log_karma(payload: RedditKarmaEntry, db: Session = Depends(get_db)):
    """Manual entry — no live Reddit OAuth polling is wired up yet (would
    need Reddit account auth beyond what REDDIT_CLIENT_ID/SECRET alone
    provide, plus a background scheduler this app doesn't have)."""
    entry = RedditKarma(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

# ---------------------------------------------------------------------------
# Reddit Intelligence — community fit, live conversation opportunities,
# and cross-community momentum signals. This observes public discussion;
# it does not automate undisclosed grassroots behavior.
# ---------------------------------------------------------------------------

from datetime import datetime as _dt
from app.models.reddit_intelligence import RedditCommunitySnapshot, RedditOpportunity


def _episode_topics(episode: Episode) -> tuple[list[str], str]:
    analysis = episode.analysis or {}
    themes = analysis.get("themes") or []
    thesis = analysis.get("thesis") or ""
    return [str(t) for t in themes], str(thesis)


@router.get("/episodes/{episode_id}/reddit/intelligence", response_model=RedditIntelligenceResponse)
def reddit_intelligence(episode_id: int, subreddits: str = Query(..., min_length=1, description="Comma-separated subreddit names"), db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    topics, thesis = _episode_topics(episode)
    names = [x.strip() for x in subreddits.split(",") if x.strip()][:8]
    communities = []
    opportunities = []
    for name in names:
        dna = reddit_service.build_community_dna(name, topics, thesis)
        communities.append(dna)
        opportunities.extend(reddit_service.find_conversation_opportunities(name, topics, thesis, limit=5))
        db.add(RedditCommunitySnapshot(
            episode_id=episode_id,
            subreddit=name.lstrip("r/").strip("/"),
            fit_score=dna["fit_score"],
            community_dna=dna,
            rules_summary=dna.get("rules", []),
        ))

    # Search only compact topical queries. The signal is observational.
    queries = list(dict.fromkeys([*(topics[:5]), thesis[:120] if thesis else ""]))
    movement = reddit_service.detect_movement_signals(queries)
    for opp in opportunities:
        db.add(RedditOpportunity(episode_id=episode_id, **opp))
    db.commit()

    return RedditIntelligenceResponse(
        episode_id=episode_id,
        communities=communities,
        opportunities=sorted(opportunities, key=lambda x: x["score"], reverse=True),
        movement_signal=movement,
        generated_at=_dt.now(timezone.utc),
    )


@router.get("/episodes/{episode_id}/reddit/opportunities", response_model=list[dict])
def list_reddit_opportunities(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    rows = db.query(RedditOpportunity).filter(RedditOpportunity.episode_id == episode_id).order_by(RedditOpportunity.score.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "subreddit": r.subreddit,
            "source_url": r.source_url,
            "opportunity_type": r.opportunity_type,
            "title": r.title,
            "rationale": r.rationale,
            "suggested_contribution": r.suggested_contribution,
            "score": r.score,
            "observed_at": r.observed_at,
        }
        for r in rows
    ]


@router.post("/reddit/movement-signal", response_model=dict)
def reddit_movement_signal(payload: RedditMovementRequest):
    if not payload.queries:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one query is required.")
    return reddit_service.detect_movement_signals(payload.queries)
