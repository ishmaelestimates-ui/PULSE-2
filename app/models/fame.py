"""
Fame module models.

Honesty framing (see app/services/fame_service.py for the full
reasoning): PULSE has no social-listening API, no citation database, and
no way to verify anything about the outside world. So:

  - FameScoreSnapshot is a DETERMINISTIC composite of PULSE's own real
    tracked numbers (Reddit engagement, campaign hype scores, coverage
    count, festival tier, milestones done) — an internal engagement
    index, not a measurement of real-world fame or authority.
  - Mention rows come from two sources: real Reddit search results
    (source="reddit", genuinely fetched), or manual entry
    (source="manual") for anything else — there's no automated web-wide
    monitoring here.
  - CompetitorBenchmark is entirely user-entered real numbers you
    looked up yourself. PULSE does not fabricate statistics about named
    third parties.
  - CulturalFootprintItem is a manual log of things you found yourself
    (a meme, a citation, a reference) — not auto-detected.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FameScoreSnapshot(Base):
    __tablename__ = "fame_score_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    components: Mapped[dict] = mapped_column(JSONB, nullable=False)  # engagement/reach_proxy/authority_proxy/momentum
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    episode: Mapped["Episode"] = relationship("Episode", back_populates="fame_snapshots")


class MentionSentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNANALYZED = "unanalyzed"


class Mention(Base):
    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # "reddit" | "manual"
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sentiment: Mapped[MentionSentiment] = mapped_column(
        Enum(MentionSentiment, name="mention_sentiment_enum"), default=MentionSentiment.UNANALYZED, nullable=False
    )
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    episode: Mapped["Episode"] = relationship("Episode", back_populates="mentions")


class CompetitorBenchmark(Base):
    """Entirely user-entered — see module docstring."""

    __tablename__ = "competitor_benchmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    competitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Subscribers"
    competitor_value: Mapped[float] = mapped_column(Float, nullable=False)
    our_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    episode: Mapped["Episode"] = relationship("Episode", back_populates="competitor_benchmarks")


class CulturalFootprintType(str, enum.Enum):
    MEME = "meme"
    REFERENCE = "reference"
    CITATION = "citation"
    OTHER = "other"


class CulturalFootprintItem(Base):
    """Manual log — see module docstring."""

    __tablename__ = "cultural_footprint_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type: Mapped[CulturalFootprintType] = mapped_column(
        Enum(CulturalFootprintType, name="cultural_footprint_type_enum"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    episode: Mapped["Episode"] = relationship("Episode", back_populates="cultural_footprint_items")
