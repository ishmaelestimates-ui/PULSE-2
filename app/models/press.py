"""
PR module models.

Honesty note on JournalistLead: PULSE has no real journalist database and
Gemini cannot reliably know current, correct names/outlets/emails for
real people — having it fabricate that would mean generating plausible-
looking but likely-wrong (or entirely invented) contact information for
real journalists. So GET /journalist-matches returns ephemeral,
unpersisted AI suggestions of *outlet types and beats* to research, never
named individuals. JournalistLead is a plain CRM record the user fills in
themselves once they've done that research (name/outlet/email start
empty/nullable) — it's tracking, not a generated contacts list.
"""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.db_compat import JSONB_COMPAT



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PressKit(Base):
    __tablename__ = "press_kits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    press_release: Mapped[str] = mapped_column(Text, nullable=False)
    # {"100": "...", "250": "...", "500": "..."}
    synopsis: Mapped[dict] = mapped_column(JSONB_COMPAT, nullable=False)
    # [{"name": "...", "bio": "..."}] — drafts, meant to be edited by a human
    bios: Mapped[list] = mapped_column(JSONB_COMPAT, nullable=False)
    # [{"text": "...", "timestamp": float, "review_id": int|null}] — text
    # pulled from the episode's own transcript, not fabricated
    quotes: Mapped[list] = mapped_column(JSONB_COMPAT, nullable=False)
    # [{"question": "...", "answer": "..."}]
    faq: Mapped[list] = mapped_column(JSONB_COMPAT, nullable=False)
    contact_info: Mapped[dict] = mapped_column(JSONB_COMPAT, nullable=False, default=dict)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="press_kit")


class JournalistLeadStatus(str, enum.Enum):
    NEW = "new"
    PITCHED = "pitched"
    REPLIED = "replied"
    DECLINED = "declined"


class JournalistLead(Base):
    """A user-maintained tracking record — NOT AI-generated. See module
    docstring."""

    __tablename__ = "journalist_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outlet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    beat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[JournalistLeadStatus] = mapped_column(
        Enum(JournalistLeadStatus, name="journalist_lead_status_enum"),
        default=JournalistLeadStatus.NEW,
        nullable=False,
    )
    # Gemini-drafted personalized pitch text, filled in when send-pitches
    # is called for this lead. Never actually emailed — see api/press.py.
    pitch_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pitched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="journalist_leads")
    embargoes: Mapped[list["Embargo"]] = relationship(
        "Embargo", back_populates="journalist_lead", cascade="all, delete-orphan"
    )


class EmbargoStatus(str, enum.Enum):
    PENDING = "pending"
    LIFTED = "lifted"
    BROKEN = "broken"


class Embargo(Base):
    __tablename__ = "embargoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    journalist_lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("journalist_leads.id", ondelete="SET NULL"), nullable=True
    )

    embargo_date: Mapped[date] = mapped_column(Date, nullable=False)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[EmbargoStatus] = mapped_column(
        Enum(EmbargoStatus, name="embargo_status_enum"),
        default=EmbargoStatus.PENDING,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="embargoes")
    journalist_lead: Mapped["JournalistLead | None"] = relationship(
        "JournalistLead", back_populates="embargoes"
    )


class Coverage(Base):
    """Manually-entered press coverage. No web scraping is implemented —
    see api/press.py docstring."""

    __tablename__ = "coverage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    outlet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    article_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="coverage_items")
