"""
ScheduledPost model.

Tracks posts PULSE has asked Postiz to schedule/publish (campaign social
posts, Reddit posts). Not a cache of Postiz's own data — Postiz remains
the source of truth for what actually happened; this is PULSE's local
record of what it requested and the last status it observed.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.db_compat import JSONB_COMPAT



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScheduledPostStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    postiz_integration_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postiz_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[ScheduledPostStatus] = mapped_column(
        Enum(ScheduledPostStatus, name="scheduled_post_status_enum"),
        default=ScheduledPostStatus.DRAFT,
        nullable=False,
    )
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Last engagement snapshot pulled from Postiz, if/when available.
    engagement_metrics: Mapped[dict | None] = mapped_column(JSONB_COMPAT, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="scheduled_posts")
