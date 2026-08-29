"""
Pydantic schemas for media upload, status, and transcription responses.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.media_file import MediaType, TranscriptionStatus


class MediaFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int
    filename: str
    file_size: int
    duration: Optional[float]
    media_type: MediaType
    transcription_status: TranscriptionStatus
    media_metadata: Optional[dict[str, Any]] = None
    uploaded_at: datetime

    # Populated by the API layer (not a DB column) so clients get a
    # ready-to-use URL rather than a filesystem path.
    url: Optional[str] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class MediaUploadResponse(BaseModel):
    media_file: MediaFileOut
    message: str = "Upload processed successfully."


class MediaStatusResponse(BaseModel):
    episode_id: int
    media_files: list[MediaFileOut]
    transcript_available: bool
    duration: Optional[float] = None


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionResponse(BaseModel):
    episode_id: int
    media_file_id: int
    transcript: str
    segments: list[TranscriptSegment] = []
    provider: str
