"""
EditorialReview model.

Each row represents a single editorial decision surfaced by analysis
(a strong moment, a weak section, a clip candidate, an opening, or a
closing) and tracks whether a human has accepted, rejected, or left it
unresolved.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.db_compat import JSONB_COMPAT



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DecisionType(str, enum.Enum):
    STRONG_MOMENT = "strong_moment"
    WEAK_SECTION = "weak_section"
    CLIP_CANDIDATE = "clip_candidate"
    OPENING = "opening"
    CLOSING = "closing"


class ReviewStatus(str, enum.Enum):
    RECOMMENDED = "recommended"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class EditorialReview(Base):
    __tablename__ = "editorial_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    decision_type: Mapped[DecisionType] = mapped_column(
        Enum(DecisionType, name="decision_type_enum"), nullable=False
    )

    # Flexible payload holding whatever fields are relevant to the
    # decision type, e.g.:
    #   strong_moment  -> {timestamp, description, confidence}
    #   weak_section   -> {start, end, reason}
    #   clip_candidate -> {start, end, hook}
    #   opening/closing-> {timestamp, description}
    decision_reference: Mapped[dict] = mapped_column(JSONB_COMPAT, nullable=False)

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status_enum"),
        default=ReviewStatus.RECOMMENDED,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="reviews")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"<EditorialReview id={self.id} type={self.decision_type} "
            f"status={self.status}>"
        )
