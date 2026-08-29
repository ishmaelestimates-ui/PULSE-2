"""
BrandSettings model.

PULSE has no authentication/user system yet (see app/api — every
endpoint is unscoped), so there is no way to store settings "per user."
This is implemented as a single global settings row instead (id is
always 1) representing the whole project/workspace. When auth is added,
add a user_id/workspace_id column and drop the singleton constraint.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BrandSettings(Base):
    __tablename__ = "brand_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    primary_color: Mapped[str] = mapped_column(String(9), default="#6C5CE7", nullable=False)
    secondary_color: Mapped[str] = mapped_column(String(9), default="#00E676", nullable=False)
    tertiary_color: Mapped[str | None] = mapped_column(String(9), nullable=True)
    font: Mapped[str] = mapped_column(String(100), default="Inter", nullable=False)

    logo_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    intro_music_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    outro_music_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BrandSettings id={self.id}>"
