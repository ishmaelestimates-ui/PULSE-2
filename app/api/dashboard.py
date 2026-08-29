"""
Executive dashboard endpoints. Aggregation and scoring are deterministic
(see app/services/dashboard_service.py) — the one exception is /risks,
which triggers a fresh sync-licensing transcript scan (a Gemini call) to
build the "Legal" risk category. /dashboard itself does NOT call that
scan (to keep the main dashboard load fast/free) — call /risks
separately for the full legal-risk picture.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campaign import CampaignPack
from app.models.dashboard import BudgetItem, ProjectMilestone
from app.models.editorial_review import EditorialReview
from app.models.episode import Episode
from app.models.film import FestivalMatch
from app.models.media_file import MediaFile
from app.models.press import PressKit
from app.models.reddit import RedditPost
from app.schemas.dashboard import (
    BudgetItemCreate,
    BudgetItemOut,
    DashboardResponse,
    FinancesResponse,
    MilestoneCreate,
    MilestoneOut,
    RisksResponse,
    TimelineResponse,
)
from app.services import dashboard_service, film_service

router = APIRouter(prefix="/api/v1/episodes", tags=["dashboard"])


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Episode {episode_id} not found.")
    return episode


@router.get("/{episode_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    media_files = db.query(MediaFile).filter(MediaFile.episode_id == episode_id).all()
    reviews = db.query(EditorialReview).filter(EditorialReview.episode_id == episode_id).all()
    campaign = db.query(CampaignPack).filter(CampaignPack.episode_id == episode_id).first()
    press_kit = db.query(PressKit).filter(PressKit.episode_id == episode_id).first()
    reddit_posts = db.query(RedditPost).filter(RedditPost.episode_id == episode_id).all()
    milestones = db.query(ProjectMilestone).filter(ProjectMilestone.episode_id == episode_id).all()
    festival_matches = db.query(FestivalMatch).filter(FestivalMatch.episode_id == episode_id).all()

    progress = dashboard_service.compute_progress(episode, media_files, reviews, campaign, press_kit, reddit_posts)
    overall = round(sum(progress.values()) / len(progress), 1) if progress else 0.0

    # Cheap risk signals only (no Gemini call) — schedule/financial/creative,
    # not legal. Call GET .../risks for the full picture including sync
    # licensing.
    budget_items = db.query(BudgetItem).filter(BudgetItem.episode_id == episode_id).all()
    cheap_risks = dashboard_service.compute_risks(episode, reviews, festival_matches, milestones, budget_items, sync_flags=[])
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for r in cheap_risks:
        severity_counts[r["severity"]] = severity_counts.get(r["severity"], 0) + 1

    health_score = dashboard_service.compute_health_score(progress, severity_counts)
    critical_path = dashboard_service.compute_critical_path(progress)

    today = date.today()
    upcoming = []
    for m in milestones:
        if m.due_date and m.status != "done" and 0 <= (m.due_date - today).days <= 30:
            upcoming.append({"type": "milestone", "title": m.title, "date": m.due_date.isoformat()})
    for f in festival_matches:
        if f.deadline and 0 <= (f.deadline - today).days <= 30:
            upcoming.append(
                {
                    "type": "festival_deadline",
                    "title": f.festival_name,
                    "date": f.deadline.isoformat(),
                    "verified": f.verified,
                }
            )
    upcoming.sort(key=lambda x: x["date"])

    return DashboardResponse(
        episode_id=episode_id,
        progress=progress,
        overall_progress=overall,
        health_score=health_score,
        critical_path=critical_path,
        upcoming_deadlines=upcoming,
    )


@router.get("/{episode_id}/risks", response_model=RisksResponse)
def get_risks(episode_id: int, db: Session = Depends(get_db)):
    episode = _get_episode_or_404(db, episode_id)
    reviews = db.query(EditorialReview).filter(EditorialReview.episode_id == episode_id).all()
    festival_matches = db.query(FestivalMatch).filter(FestivalMatch.episode_id == episode_id).all()
    milestones = db.query(ProjectMilestone).filter(ProjectMilestone.episode_id == episode_id).all()
    budget_items = db.query(BudgetItem).filter(BudgetItem.episode_id == episode_id).all()

    sync_flags = []
    if episode.transcript and episode.transcript.strip():
        sync_flags = film_service.scan_sync_licensing(episode.transcript)

    risks = dashboard_service.compute_risks(episode, reviews, festival_matches, milestones, budget_items, sync_flags)
    return RisksResponse(episode_id=episode_id, risks=risks)


@router.get("/{episode_id}/finances", response_model=FinancesResponse)
def get_finances(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    items = db.query(BudgetItem).filter(BudgetItem.episode_id == episode_id).all()
    totals = dashboard_service.compute_finances(items)
    return FinancesResponse(episode_id=episode_id, items=items, **totals)


@router.post("/{episode_id}/finances", response_model=BudgetItemOut, status_code=status.HTTP_201_CREATED)
def add_budget_item(episode_id: int, payload: BudgetItemCreate, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    item = BudgetItem(episode_id=episode_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{episode_id}/timeline", response_model=TimelineResponse)
def get_timeline(episode_id: int, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    milestones = (
        db.query(ProjectMilestone).filter(ProjectMilestone.episode_id == episode_id).order_by(ProjectMilestone.due_date).all()
    )
    today = date.today()
    out = []
    for m in milestones:
        item = MilestoneOut.model_validate(m)
        item.overdue = bool(m.due_date and m.status != "done" and m.due_date < today)
        out.append(item)
    return TimelineResponse(episode_id=episode_id, milestones=out)


@router.post("/{episode_id}/timeline", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED)
def add_milestone(episode_id: int, payload: MilestoneCreate, db: Session = Depends(get_db)):
    _get_episode_or_404(db, episode_id)
    milestone = ProjectMilestone(episode_id=episode_id, **payload.model_dump())
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    out = MilestoneOut.model_validate(milestone)
    out.overdue = False
    return out
