"""
ColorGrade model.

Records one applied color treatment for an episode's primary video —
either a built-in/user LUT (`source=lut`) or Gemini-suggested grading
parameters (`source=style_transfer`). Kept as a log (one row per
application, not an upsert) so an editor can see and compare past
attempts.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.db_compat import JSONB_COMPAT



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ColorGradeSource(str, enum.Enum):
    LUT = "lut"
    STYLE_TRANSFER = "style_transfer"


class ColorGrade(Base):
    __tablename__ = "color_grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source: Mapped[ColorGradeSource] = mapped_column(
        Enum(ColorGradeSource, name="color_grade_source_enum"), nullable=False
    )

    # Set when source=lut
    lut_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Set when source=style_transfer: Gemini's suggested grading
    # parameters (brightness/contrast/saturation/gamma/temperature/tint)
    # plus its written rationale.
    style_transfer_params: Mapped[dict | None] = mapped_column(JSONB_COMPAT, nullable=True)
    reference_image_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Always populated: a fast single-frame preview with the grade applied.
    preview_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Only populated if a full video render was requested (render_full=true).
    graded_media_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="color_grades")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ColorGrade id={self.id} episode_id={self.episode_id} source={self.source}>"
