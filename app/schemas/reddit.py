"""
Pydantic schemas for Reddit distribution and Postiz-backed scheduling.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.reddit import RedditPostStatus
from app.models.scheduled_post import ScheduledPostStatus


class SubredditSearchResult(BaseModel):
    name: str
    subscribers: Optional[int] = None
    active_users: Optional[int] = None
    description: Optional[str] = None
    over_18: bool = False


class SubredditSearchResponse(BaseModel):
    query: str
    results: list[SubredditSearchResult]


class SubredditAnalysis(BaseModel):
    name: str
    subscribers: Optional[int] = None
    active_users: Optional[int] = None
    description: Optional[str] = None
    rules_summary: list[str] = []
    top_posts: list[dict[str, Any]] = []
    note: str = (
        "Peak-activity-time analysis isn't available — that needs "
        "historical post-performance data PULSE doesn't collect. "
        "Subscriber/active-user counts and rules are read live from "
        "Reddit's public API."
    )


class RedditGenerateResponse(BaseModel):
    episode_id: int
    title_options: list[str]
    body: str
    flair_suggestions: list[str]
    recommended_subreddits: list[SubredditSearchResult]
    disclosure_note: str
    note: str = (
        "Titles favor genuine curiosity over clickbait, and the body "
        "discloses that this is the show's own creator posting. Verify "
        "each subreddit's self-promotion rules before posting — many "
        "require a mix of non-promotional participation first."
    )


class RedditPostCreate(BaseModel):
    subreddit: str
    title: str
    body: str
    flair: Optional[str] = None


class RedditPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    subreddit: str
    title: str
    body: str
    flair: Optional[str]
    disclosure_note: str
    status: RedditPostStatus
    scheduled_time: Optional[datetime]
    postiz_post_id: Optional[str]
    posted_at: Optional[datetime]
    upvotes: int
    comment_count: int
    last_checked_at: Optional[datetime]
    created_at: datetime


class RedditScheduleRequest(BaseModel):
    reddit_post_id: int
    scheduled_time: Optional[datetime] = None  # omit to post ASAP via Postiz
    postiz_integration_id: str


class RedditCommentSuggestRequest(BaseModel):
    comment_body: str
    episode_context: Optional[str] = None


class RedditCommentSuggestResponse(BaseModel):
    comment_body: str
    suggested_reply: str
    note: str = (
        "Drafted for you (the disclosed creator) to review and post "
        "yourself — PULSE does not post to Reddit on your behalf."
    )


class RedditKarmaEntry(BaseModel):
    total_karma: int
    post_karma: int
    comment_karma: int
    source: str = "manual"


class RedditKarmaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recorded_at: datetime
    total_karma: int
    post_karma: int
    comment_karma: int
    source: str


class ScheduledPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    platform: str
    content_text: str
    postiz_integration_id: Optional[str]
    postiz_post_id: Optional[str]
    status: ScheduledPostStatus
    scheduled_time: Optional[datetime]
    engagement_metrics: Optional[dict[str, Any]]
    last_error: Optional[str]
    created_at: datetime


class SchedulePostsRequest(BaseModel):
    # platform -> postiz integration id (channel). Only platforms present
    # here get scheduled.
    platform_integrations: dict[str, str]
    scheduled_time: Optional[datetime] = None


class SchedulePostsResponse(BaseModel):
    episode_id: int
    scheduled: list[ScheduledPostOut]


class PlatformIntegrationOut(BaseModel):
    id: str
    name: str
    identifier: str
    disabled: bool
