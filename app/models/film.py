"""
Film feature models.

Honesty notes (see services for full framing):
  - FestivalMatch rows start life as Gemini's suggestions — deadlines and
    entry fees are the model's best guess from training data, which goes
    stale (festival dates move every year) and can simply be wrong.
    `verified` defaults False and stays False until a human confirms
    against the festival's actual site; `deadline`/`entry_fee` are
    nullable and editable via PATCH once corrected.
  - TerritoryRelease is a planning tool (target dates you're aiming for),
    not a record of real distribution deals — PULSE has no distribution
    partners integration.
"""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FilmAct(Base):
    __tablename__ = "film_acts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    act_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, or 3
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # Gemini's self-rated confidence

    episode: Mapped["Episode"] = relationship("Episode", back_populates="film_acts")


class TrailerCut(Base):
    __tablename__ = "trailer_cuts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)  # 30, 60, or 90 (seconds)
    clip_order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # AI's qualitative read of tone for CSV marker coloring, not an
    # objective classification — see film_service.py
    scene_type: Mapped[str] = mapped_column(String(50), default="Dialogue", nullable=False)
    review_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    episode: Mapped["Episode"] = relationship("Episode", back_populates="trailer_cuts")


class FestivalTier(int, enum.Enum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


class FestivalMatchStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class FestivalMatch(Base):
    __tablename__ = "festival_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    festival_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    why_relevant: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI-suggested, unverified until a human checks the festival's site.
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    entry_fee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[FestivalMatchStatus] = mapped_column(
        Enum(FestivalMatchStatus, name="festival_match_status_enum"),
        default=FestivalMatchStatus.SUGGESTED,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="festival_matches")


class TerritoryReleaseStatus(str, enum.Enum):
    PLANNED = "planned"
    RELEASED = "released"


class TerritoryRelease(Base):
    """A planning target, not a real distribution deal record — see
    module docstring."""

    __tablename__ = "territory_releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    territory: Mapped[str] = mapped_column(String(100), nullable=False)
    release_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TerritoryReleaseStatus] = mapped_column(
        Enum(TerritoryReleaseStatus, name="territory_release_status_enum"),
        default=TerritoryReleaseStatus.PLANNED,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    episode: Mapped["Episode"] = relationship("Episode", back_populates="territory_releases")
