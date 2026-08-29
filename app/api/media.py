"""
Media endpoints: file upload (with FFmpeg-derived metadata/thumbnail/
waveform), media status, and transcription.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.episode import Episode
from app.models.media_file import MediaFile, MediaType, TranscriptionStatus
from app.schemas.media import (
    MediaFileOut,
    MediaStatusResponse,
    MediaUploadResponse,
    TranscriptionResponse,
)
from app.services import media_service, transcription_service, color_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/episodes", tags=["media"])


def _get_episode_or_404(db: Session, episode_id: int) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Episode {episode_id} not found.",
        )
    return episode


def _get_media_file_or_404(db: Session, episode_id: int, media_file_id: int) -> MediaFile:
    media_file = (
        db.query(MediaFile)
        .filter(MediaFile.id == media_file_id, MediaFile.episode_id == episode_id)
        .first()
    )
    if media_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media file {media_file_id} not found for episode {episode_id}.",
        )
    return media_file


def _to_media_file_out(media_file: MediaFile) -> MediaFileOut:
    out = MediaFileOut.model_validate(media_file)
    out.url = media_service.build_media_url(Path(media_file.file_path))
    if media_file.audio_path:
        out.audio_url = media_service.build_media_url(Path(media_file.audio_path))
    if media_file.thumbnail_path:
        out.thumbnail_url = media_service.build_media_url(Path(media_file.thumbnail_path))
    return out


@router.post(
    "/{episode_id}/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    episode_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload an audio or video file for an episode. Validates the
    extension, stores the file, then runs FFmpeg to extract metadata
    (duration/codec/resolution), a standardized audio track, a waveform,
    and (for video) a first-frame thumbnail."""
    episode = _get_episode_or_404(db, episode_id)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided."
        )

    media_type = media_service.classify_media_type(file.filename)
    stored_path, file_size = await media_service.save_upload(episode_id, file)

    try:
        metadata = media_service.probe_metadata(stored_path)
        audio_path = media_service.extract_audio(stored_path, episode_id)
        metadata["waveform"] = media_service.generate_waveform(audio_path)

        # Real loudness measurement (ffmpeg loudnorm analysis pass), used
        # by the delivery-spec compliance check in the Coloring tab. Not
        # fatal if it fails — compliance checks just report "unknown".
        try:
            loudness = color_service.measure_loudness(audio_path)
            metadata.update(loudness)
        except HTTPException as loud_exc:
            logger.warning(
                "Loudness measurement failed for episode %s: %s",
                episode_id,
                loud_exc.detail,
            )

        thumbnail_path = None
        if media_type == MediaType.VIDEO:
            thumbnail_path = media_service.generate_thumbnail(stored_path, episode_id)
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise

    media_file = MediaFile(
        episode_id=episode_id,
        filename=file.filename,
        file_path=str(stored_path),
        file_size=file_size,
        duration=metadata.get("duration"),
        media_type=media_type,
        audio_path=str(audio_path),
        thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        transcription_status=TranscriptionStatus.NONE,
        media_metadata=metadata,
    )
    db.add(media_file)

    # Keep the episode's top-level duration in sync with its primary
    # media asset if it wasn't already set.
    if episode.duration is None and metadata.get("duration"):
        episode.duration = metadata["duration"]
        db.add(episode)

    db.commit()
    db.refresh(media_file)

    return MediaUploadResponse(media_file=_to_media_file_out(media_file))


@router.get("/{episode_id}/media-status", response_model=MediaStatusResponse)
def media_status(episode_id: int, db: Session = Depends(get_db)):
    """Return every uploaded media file for this episode, its
    transcription status, and whether the episode has a transcript yet."""
    episode = _get_episode_or_404(db, episode_id)
    media_files = (
        db.query(MediaFile)
        .filter(MediaFile.episode_id == episode_id)
        .order_by(MediaFile.id)
        .all()
    )

    return MediaStatusResponse(
        episode_id=episode_id,
        media_files=[_to_media_file_out(m) for m in media_files],
        transcript_available=bool(episode.transcript and episode.transcript.strip()),
        duration=episode.duration,
    )


@router.post("/{episode_id}/transcribe", response_model=TranscriptionResponse)
def transcribe_episode(
    episode_id: int,
    media_file_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Transcribe an episode's audio via the configured provider (Gemini
    or Whisper) and store the result on the Episode. If media_file_id is
    omitted, the most recently uploaded media file is used."""
    episode = _get_episode_or_404(db, episode_id)

    if media_file_id is not None:
        media_file = _get_media_file_or_404(db, episode_id, media_file_id)
    else:
        media_file = (
            db.query(MediaFile)
            .filter(MediaFile.episode_id == episode_id)
            .order_by(MediaFile.id.desc())
            .first()
        )
        if media_file is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No media files uploaded for episode {episode_id}. "
                    "Upload one via POST /api/v1/episodes/{episode_id}/media first."
                ),
            )

    if not media_file.audio_path or not Path(media_file.audio_path).exists():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This media file has no extracted audio track available to transcribe.",
        )

    media_file.transcription_status = TranscriptionStatus.PENDING
    db.add(media_file)
    db.commit()

    try:
        result = transcription_service.transcribe_audio(
            Path(media_file.audio_path), episode_id, media_file.id
        )
    except HTTPException:
        media_file.transcription_status = TranscriptionStatus.FAILED
        db.add(media_file)
        db.commit()
        raise
    except Exception:
        media_file.transcription_status = TranscriptionStatus.FAILED
        db.add(media_file)
        db.commit()
        logger.exception("Unexpected transcription failure")
        raise

    media_file.transcription_status = TranscriptionStatus.COMPLETE
    episode.transcript = result.transcript
    episode.transcript_segments = [s.model_dump() for s in result.segments]
    db.add(media_file)
    db.add(episode)
    db.commit()

    return result
