"""
Episode model.

An Episode represents a single podcast episode: its transcript, its
duration, and the raw analysis payload returned by Gemini. Individual
editorial decisions derived from that analysis live in EditorialReview
rows (see app/models/editorial_review.py), linked via `episode_id`.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.db_compat import JSONB_COMPAT


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Nullable as of Night 2: an episode can now be created from a media
    # upload before any transcript exists, with the transcript filled in
    # later by POST /api/v1/episodes/{id}/transcribe. Text-first episodes
    # (Night 1 flow) can still supply a transcript at creation time.
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw analysis payload returned by Gemini, kept alongside the
    # normalized EditorialReview rows for auditability/debugging.
    analysis: Mapped[dict | None] = mapped_column(JSONB_COMPAT, nullable=True)

    # Segment-level transcript timestamps (list of {start, end, text}),
    # populated by POST /transcribe. Kept separate from `transcript`
    # (the flattened full text) so the frontend can sync playback to the
    # transcript without re-deriving offsets from plain text.
    transcript_segments: Mapped[list | None] = mapped_column(JSONB_COMPAT, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    reviews: Mapped[list["EditorialReview"]] = relationship(
        "EditorialReview",
        back_populates="episode",
        cascade="all, delete-orphan",
        order_by="EditorialReview.id",
    )

    media_files: Mapped[list["MediaFile"]] = relationship(
        "MediaFile",
        back_populates="episode",
        cascade="all, delete-orphan",
        order_by="MediaFile.id",
    )

    color_grades: Mapped[list["ColorGrade"]] = relationship(
        "ColorGrade",
        back_populates="episode",
        cascade="all, delete-orphan",
        order_by="ColorGrade.id",
    )

    campaign_pack: Mapped["CampaignPack | None"] = relationship(
        "CampaignPack",
        back_populates="episode",
        cascade="all, delete-orphan",
        uselist=False,
    )

    press_kit: Mapped["PressKit | None"] = relationship(
        "PressKit", back_populates="episode", cascade="all, delete-orphan", uselist=False
    )
    journalist_leads: Mapped[list["JournalistLead"]] = relationship(
        "JournalistLead", back_populates="episode", cascade="all, delete-orphan"
    )
    embargoes: Mapped[list["Embargo"]] = relationship(
        "Embargo", back_populates="episode", cascade="all, delete-orphan"
    )
    coverage_items: Mapped[list["Coverage"]] = relationship(
        "Coverage", back_populates="episode", cascade="all, delete-orphan"
    )
    reddit_posts: Mapped[list["RedditPost"]] = relationship(
        "RedditPost", back_populates="episode", cascade="all, delete-orphan"
    )
    scheduled_posts: Mapped[list["ScheduledPost"]] = relationship(
        "ScheduledPost", back_populates="episode", cascade="all, delete-orphan"
    )

    film_acts: Mapped[list["FilmAct"]] = relationship(
        "FilmAct", back_populates="episode", cascade="all, delete-orphan"
    )
    trailer_cuts: Mapped[list["TrailerCut"]] = relationship(
        "TrailerCut", back_populates="episode", cascade="all, delete-orphan"
    )
    festival_matches: Mapped[list["FestivalMatch"]] = relationship(
        "FestivalMatch", back_populates="episode", cascade="all, delete-orphan"
    )
    territory_releases: Mapped[list["TerritoryRelease"]] = relationship(
        "TerritoryRelease", back_populates="episode", cascade="all, delete-orphan"
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(
        "ProjectMilestone", back_populates="episode", cascade="all, delete-orphan"
    )
    budget_items: Mapped[list["BudgetItem"]] = relationship(
        "BudgetItem", back_populates="episode", cascade="all, delete-orphan"
    )

    fame_snapshots: Mapped[list["FameScoreSnapshot"]] = relationship(
        "FameScoreSnapshot", back_populates="episode", cascade="all, delete-orphan"
    )
    mentions: Mapped[list["Mention"]] = relationship(
        "Mention", back_populates="episode", cascade="all, delete-orphan"
    )
    competitor_benchmarks: Mapped[list["CompetitorBenchmark"]] = relationship(
        "CompetitorBenchmark", back_populates="episode", cascade="all, delete-orphan"
    )
    cultural_footprint_items: Mapped[list["CulturalFootprintItem"]] = relationship(
        "CulturalFootprintItem", back_populates="episode", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Episode id={self.id} title={self.title!r}>"
