"""
Reddit distribution models.

Framing note: this module deliberately does NOT implement "post as
organic discussion, no self-promotion" tooling — that's asking for help
disguising marketing as authentic community discussion, which is
deceptive to the people reading it and against most subreddits' actual
rules. What's built instead: posts carry an explicit disclosure_note
(e.g. "Posted by the show's creator"), title/body generation is optimized
for genuine curiosity rather than clickbait, and subreddit selection
surfaces each subreddit's real self-promotion rules so the user follows
them rather than evades them. See app/services/reddit_service.py.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RedditPostStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    REMOVED = "removed"


class RedditPost(Base):
    __tablename__ = "reddit_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    subreddit: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    flair: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Always populated — see module docstring. Not optional, not editable
    # to empty via the API.
    disclosure_note: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Posted by the show's creator."
    )

    status: Mapped[RedditPostStatus] = mapped_column(
        Enum(RedditPostStatus, name="reddit_post_status_enum"),
        default=RedditPostStatus.DRAFT,
        nullable=False,
    )

    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    postiz_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Performance — populated manually or via Postiz analytics lookup,
    # never fabricated.
    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="reddit_posts")
    comments: Mapped[list["RedditComment"]] = relationship(
        "RedditComment", back_populates="post", cascade="all, delete-orphan"
    )


class RedditComment(Base):
    """A drafted reply for the creator's own disclosed account to post
    themselves — not an automated/undisclosed reply bot. `approved` gates
    nothing automatically (PULSE doesn't post comments on your behalf);
    it's just a tracking flag for the human workflow."""

    __tablename__ = "reddit_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reddit_post_id: Mapped[int] = mapped_column(
        ForeignKey("reddit_posts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    comment_body: Mapped[str] = mapped_column(Text, nullable=False)  # the comment being replied to
    suggested_reply: Mapped[str] = mapped_column(Text, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    post: Mapped["RedditPost"] = relationship("RedditPost", back_populates="comments")


class RedditKarma(Base):
    """A manually-logged (or Postiz-analytics-backed, if configured)
    karma reading over time. No automatic background polling — there's
    no scheduler in this app yet."""

    __tablename__ = "reddit_karma"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    total_karma: Mapped[int] = mapped_column(Integer, nullable=False)
    post_karma: Mapped[int] = mapped_column(Integer, nullable=False)
    comment_karma: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
