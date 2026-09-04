"""
Media service: file storage helpers plus FFmpeg-backed extraction of
metadata, audio, thumbnails, and a simplified waveform.

FFmpeg/ffprobe must be installed and on PATH (the provided Dockerfile
installs them via apt). If they're missing, every function here raises a
clean HTTPException rather than a raw FileNotFoundError/CalledProcessError,
so the API layer doesn't need its own try/except boilerplate.
"""
import shutil
import struct
import subprocess
import uuid
from pathlib import Path

import aiofiles
import ffmpeg
from fastapi import HTTPException, UploadFile, status

from app.config import get_settings
from app.models.media_file import MediaType

# Extensions we accept, mapped to whether they're audio or video.
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".aac"}
ALLOWED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Chunk size for streaming uploads to disk without loading the whole file
# into memory.
_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "ffmpeg/ffprobe not found on PATH. Install FFmpeg on the "
                "host (or use the provided Dockerfile, which installs it) "
                "before uploading media."
            ),
        )


def classify_media_type(filename: str) -> MediaType:
    ext = Path(filename).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    if ext in AUDIO_EXTENSIONS:
        return MediaType.AUDIO
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Unsupported file extension '{ext}'. Allowed: "
            f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
        ),
    )


def build_media_url(path: Path) -> str:
    """Build the application URL for a stored media file.

    The current frontend uses same-origin media URLs, so authorization is
    still enforced at the application/API boundary before exposing metadata.
    A signed-download or cookie-based media layer should replace the static
    mount before handling highly confidential unreleased media on the open
    internet.
    """
    settings = get_settings()
    root = Path(settings.media_storage_path).resolve()
    relative = path.resolve().relative_to(root)
    return f"/media/{relative.as_posix()}"


def episode_media_dir(episode_id: int) -> Path:
    settings = get_settings()
    directory = Path(settings.media_storage_path) / "uploads" / str(episode_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def derived_media_dir(episode_id: int) -> Path:
    """Directory for ffmpeg-derived assets (extracted audio, thumbnails)."""
    settings = get_settings()
    directory = Path(settings.media_storage_path) / "derived" / str(episode_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def save_upload(episode_id: int, upload: UploadFile) -> tuple[Path, int]:
    """Stream an UploadFile to disk under the episode's upload directory.
    Returns (path, size_in_bytes). Raises HTTPException if the file is
    empty or exceeds the configured max size."""
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    ext = Path(upload.filename or "").suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    destination = episode_media_dir(episode_id) / unique_name

    size = 0
    try:
        async with aiofiles.open(destination, "wb") as out_file:
            while chunk := await upload.read(_UPLOAD_CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"File exceeds the {settings.max_upload_size_mb}MB "
                            "upload limit."
                        ),
                    )
                await out_file.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:  # noqa: BLE001
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {exc}",
        ) from exc

    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    return destination, size


def probe_metadata(path: Path) -> dict:
    """Run ffprobe (via ffmpeg-python's probe helper) and return a
    normalized dict of duration/codec/resolution/etc."""
    _require_ffmpeg()
    try:
        info = ffmpeg.probe(str(path))
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else str(exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ffprobe could not read this file (is it a valid media file?): {stderr[:500]}",
        ) from exc

    fmt = info.get("format", {})
    duration = float(fmt["duration"]) if fmt.get("duration") else None

    video_stream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "video"), None
    )
    audio_stream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None
    )

    metadata: dict = {"duration": duration, "format_name": fmt.get("format_name")}

    if video_stream:
        metadata["video_codec"] = video_stream.get("codec_name")
        metadata["width"] = video_stream.get("width")
        metadata["height"] = video_stream.get("height")
        metadata["resolution"] = (
            f"{video_stream.get('width')}x{video_stream.get('height')}"
            if video_stream.get("width") and video_stream.get("height")
            else None
        )
        fps_raw = video_stream.get("r_frame_rate")  # e.g. "30000/1001"
        if fps_raw and "/" in fps_raw:
            num, den = fps_raw.split("/")
            try:
                metadata["frame_rate"] = round(float(num) / float(den), 3)
            except ZeroDivisionError:
                metadata["frame_rate"] = None

    if audio_stream:
        metadata["audio_codec"] = audio_stream.get("codec_name")
        metadata["sample_rate"] = audio_stream.get("sample_rate")
        metadata["channels"] = audio_stream.get("channels")

    return metadata


def extract_audio(source_path: Path, episode_id: int) -> Path:
    """Transcode the audio track of `source_path` to a standardized mono
    16kHz WAV file, suitable for both transcription and waveform
    generation. Used for both video sources (pulls the audio stream) and
    audio sources (normalizes format)."""
    _require_ffmpeg()
    output_path = derived_media_dir(episode_id) / f"{source_path.stem}_audio.wav"

    try:
        (
            ffmpeg.input(str(source_path))
            .output(
                str(output_path),
                ac=1,
                ar=16000,
                acodec="pcm_s16le",
                vn=None,  # drop any video stream
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else str(exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ffmpeg failed to extract audio: {stderr[:500]}",
        ) from exc

    return output_path


def generate_thumbnail(video_path: Path, episode_id: int) -> Path:
    """Grab the first frame of a video as a JPEG thumbnail."""
    _require_ffmpeg()
    output_path = derived_media_dir(episode_id) / f"{video_path.stem}_thumb.jpg"

    try:
        (
            ffmpeg.input(str(video_path), ss=0)
            .output(str(output_path), vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else str(exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ffmpeg failed to generate thumbnail: {stderr[:500]}",
        ) from exc

    return output_path


def generate_waveform(audio_path: Path, num_points: int = 300) -> list[float]:
    """Produce a simplified waveform as a list of `num_points` floats in
    [0, 1], each representing the peak amplitude of one time bucket.
    Decodes to raw mono 8kHz PCM via ffmpeg and processes it in pure
    Python (no numpy dependency) to keep the image lightweight."""
    _require_ffmpeg()
    sample_rate = 8000

    cmd = [
        "ffmpeg",
        "-i",
        str(audio_path),
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-v",
        "error",
        "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else str(exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ffmpeg failed to decode audio for waveform generation: {stderr[:500]}",
        ) from exc

    raw = result.stdout
    sample_count = len(raw) // 2  # 16-bit samples
    if sample_count == 0:
        return [0.0] * num_points

    samples = struct.unpack(f"<{sample_count}h", raw[: sample_count * 2])

    bucket_size = max(1, sample_count // num_points)
    waveform: list[float] = []
    for i in range(0, sample_count, bucket_size):
        bucket = samples[i : i + bucket_size]
        if not bucket:
            continue
        peak = max(abs(s) for s in bucket)
        waveform.append(round(peak / 32768.0, 4))

    # Pad/truncate to exactly num_points so clients can rely on a fixed
    # length regardless of source duration.
    if len(waveform) < num_points:
        waveform.extend([0.0] * (num_points - len(waveform)))
    else:
        waveform = waveform[:num_points]

    return waveform
