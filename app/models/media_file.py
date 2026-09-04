"""
MediaFile model.

Represents a single uploaded media asset (audio or video) attached to an
Episode. FFmpeg-derived metadata (duration, codec, resolution, waveform,
thumbnail path) lives in the `media_metadata` JSONB column so we don't
need a schema migration every time we want to capture a new derived
field.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.db_compat import JSONB_COMPAT



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MediaType(str, enum.Enum):
    AUDIO = "audio"
    VIDEO = "video"


class TranscriptionStatus(str, enum.Enum):
    NONE = "none"
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type_enum"), nullable=False
    )

    # Path to extracted audio (set when the upload was video and we pulled
    # an audio-only copy out for transcription/waveform purposes).
    audio_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    transcription_status: Mapped[TranscriptionStatus] = mapped_column(
        Enum(TranscriptionStatus, name="transcription_status_enum"),
        default=TranscriptionStatus.NONE,
        nullable=False,
    )

    # codec, resolution (video only), waveform (list[float]), and any
    # other ffprobe/ffmpeg-derived data.
    media_metadata: Mapped[dict | None] = mapped_column(JSONB_COMPAT, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="media_files")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<MediaFile id={self.id} episode_id={self.episode_id} filename={self.filename!r}>"
