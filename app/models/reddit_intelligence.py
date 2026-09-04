"""Persistent Reddit community intelligence snapshots.

These records capture observations PULSE made from public Reddit data. They are
not used to manufacture grassroots activity or impersonate community members.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RedditCommunitySnapshot(Base):
    __tablename__ = "reddit_community_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    community_dna: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rules_summary: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    episode: Mapped["Episode"] = relationship("Episode")


class RedditOpportunity(Base):
    __tablename__ = "reddit_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    subreddit: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    opportunity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_contribution: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    episode: Mapped["Episode"] = relationship("Episode")
