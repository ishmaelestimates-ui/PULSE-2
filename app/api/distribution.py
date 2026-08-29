"""
Postiz-backed distribution endpoints: scheduling the campaign pack's
social posts across connected channels, checking status, and listing
connected platforms.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campaign import CampaignPack
from app.models.episode import Episode
from app.models.scheduled_post import ScheduledPost, ScheduledPostStatus
from app.schemas.reddit import (
    PlatformIntegrationOut,
    ScheduledPostOut,
    SchedulePostsRequest,
    SchedulePostsResponse,
)
from app.services import postiz_service

router = APIRouter(prefix="/api/v1", tags=["distribution"])


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Episode {episode_id} not found.")
    return episode


@router.get("/platforms/integrations", response_model=list[PlatformIntegrationOut])
def list_platform_integrations():
    """Every channel connected in Postiz, for mapping a platform name to
    the integration id `schedule-posts` needs."""
    integrations = postiz_service.list_integrations()
    return [
        PlatformIntegrationOut(
            id=i.get("id", ""), name=i.get("name", ""), identifier=i.get("identifier", ""), disabled=i.get("disabled", False)
        )
        for i in integrations
    ]


@router.get("/platforms/reddit/status")
def reddit_platform_status():
    integrations = postiz_service.list_integrations()
    reddit_integrations = [i for i in integrations if i.get("identifier") == "reddit"]
    return {
        "connected": len(reddit_integrations) > 0,
        "integrations": reddit_integrations,
    }


@router.post("/episodes/{episode_id}/schedule-posts", response_model=SchedulePostsResponse)
def schedule_posts(episode_id: int, payload: SchedulePostsRequest, db: Session = Depends(get_db)):
    """Sends the campaign pack's per-platform social post text to Postiz
    for each platform present in `platform_integrations`. Requires a
    campaign pack to already exist (POST .../generate-campaign)."""
    _get_episode_or_404(db, episode_id)
    pack = db.query(CampaignPack).filter(CampaignPack.episode_id == episode_id).first()
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No campaign generated yet. Run POST .../generate-campaign first.",
        )

    scheduled_iso = payload.scheduled_time.isoformat() if payload.scheduled_time else None
    post_type = "schedule" if payload.scheduled_time else "now"

    results = []
    for platform, integration_id in payload.platform_integrations.items():
        post_data = pack.social_posts.get(platform)
        if not post_data:
            continue
        content_text = post_data["text"]
        if post_data.get("hashtags"):
            content_text += "\n\n" + " ".join(f"#{h.lstrip('#')}" for h in post_data["hashtags"])

        record = ScheduledPost(
            episode_id=episode_id,
            platform=platform,
            content_text=content_text,
            postiz_integration_id=integration_id,
            scheduled_time=payload.scheduled_time,
        )
        try:
            result = postiz_service.create_post(integration_id, content_text, post_type=post_type, scheduled_iso=scheduled_iso)
            record.postiz_post_id = str(result.get("id")) if isinstance(result, dict) and result.get("id") else None
            record.status = ScheduledPostStatus.SCHEDULED
        except HTTPException as exc:
            record.status = ScheduledPostStatus.FAILED
            record.last_error = str(exc.detail)

        db.add(record)
        results.append(record)

    db.commit()
    for r in results:
        db.refresh(r)
    return SchedulePostsResponse(episode_id=episode_id, scheduled=results)


@router.get("/episodes/{episode_id}/post-status", response_model=list[ScheduledPostOut])
def post_status(episode_id: int, db: Session = Depends(get_db)):
    """Refreshes each scheduled post's status/engagement from Postiz
    where possible, then returns everything PULSE has on record."""
    _get_episode_or_404(db, episode_id)
    posts = db.query(ScheduledPost).filter(ScheduledPost.episode_id == episode_id).all()

    for post in posts:
        if not post.postiz_post_id:
            continue
        data = postiz_service.get_post_status(post.postiz_post_id)
        if data.get("status") and data.get("status") != "unknown":
            post.engagement_metrics = data.get("metrics") or data.get("engagement")
            db.add(post)

    db.commit()
    return posts
