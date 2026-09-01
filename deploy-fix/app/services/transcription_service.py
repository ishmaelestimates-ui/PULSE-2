"""
Transcription service.

Supports two providers, selected via TRANSCRIPTION_PROVIDER:
  - "gemini":  uploads the audio file to the Gemini Files API and asks
               Gemini 1.5 Flash to transcribe it with timestamps.
  - "whisper": calls OpenAI's hosted Whisper API (audio.transcriptions),
               which returns word/segment-level timestamps directly.

Note on "openai-whisper": that PyPI package is the *local* model — it
downloads multi-GB checkpoints and needs a GPU to be fast, which is a
poor fit for a stateless API backend. This service instead calls OpenAI's
hosted Whisper endpoint via the lightweight `openai` client. If you
specifically want fully local/offline transcription, swap the whisper
branch below for `openai-whisper` or `faster-whisper`.
"""
import json
import logging
import re
import time
from pathlib import Path

import google.generativeai as genai
from fastapi import HTTPException, status
from openai import OpenAI, OpenAIError

from app.config import get_settings
from app.schemas.media import TranscriptionResponse, TranscriptSegment

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

GEMINI_TRANSCRIBE_PROMPT = """Transcribe this audio in full. Return ONLY a \
JSON object (no markdown fences, no commentary) with this exact shape:

{
  "segments": [
    {"start": <seconds:float>, "end": <seconds:float>, "text": <string>}
  ]
}

Segment the transcript into natural phrases or sentences with accurate \
start/end timestamps in seconds. Do not omit any spoken content.
"""


def _strip_code_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _transcribe_with_gemini(audio_path: Path) -> tuple[str, list[TranscriptSegment]]:
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your-key-here":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured.",
        )
    genai.configure(api_key=settings.gemini_api_key)

    try:
        uploaded = genai.upload_file(str(audio_path))
        # Gemini processes uploaded files asynchronously; poll until ready.
        while uploaded.state.name == "PROCESSING":
            time.sleep(1)
            uploaded = genai.get_file(uploaded.name)
        if uploaded.state.name == "FAILED":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini failed to process the uploaded audio file.",
            )

        model = genai.GenerativeModel(settings.gemini_model)
        response = model.generate_content(
            [uploaded, GEMINI_TRANSCRIBE_PROMPT],
            generation_config={
                "temperature": 0.0,
                "response_mime_type": "application/json",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini transcription request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini transcription request failed: {exc}",
        ) from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini returned an empty transcription response.",
        )

    cleaned = _strip_code_fence(raw_text)
    try:
        payload = json.loads(cleaned)
        segments_raw = payload["segments"]
        segments = [TranscriptSegment.model_validate(s) for s in segments_raw]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("Failed to parse Gemini transcription response: %s", cleaned)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini transcription response did not match the expected schema.",
        ) from exc

    full_text = " ".join(s.text.strip() for s in segments).strip()
    return full_text, segments


def _transcribe_with_whisper(audio_path: Path) -> tuple[str, list[TranscriptSegment]]:
    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key == "your-openai-key-here":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured.",
        )

    client = OpenAI(api_key=settings.openai_api_key)

    try:
        with open(audio_path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model=settings.whisper_model,
                file=audio_file,
                response_format="verbose_json",
            )
    except OpenAIError as exc:
        logger.exception("Whisper API request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Whisper API request failed: {exc}",
        ) from exc

    segments = [
        TranscriptSegment(start=seg.start, end=seg.end, text=seg.text.strip())
        for seg in getattr(result, "segments", []) or []
    ]
    full_text = (result.text or "").strip()

    if not segments and full_text:
        # verbose_json should include segments, but fall back to a single
        # unsegmented block if the API ever omits them.
        segments = [TranscriptSegment(start=0.0, end=0.0, text=full_text)]

    return full_text, segments


def transcribe_audio(
    audio_path: Path, episode_id: int, media_file_id: int
) -> TranscriptionResponse:
    """Dispatch to the configured provider and return a normalized
    TranscriptionResponse."""
    settings = get_settings()
    provider = settings.transcription_provider.lower()

    if provider == "gemini":
        full_text, segments = _transcribe_with_gemini(audio_path)
    elif provider == "whisper":
        full_text, segments = _transcribe_with_whisper(audio_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown TRANSCRIPTION_PROVIDER '{provider}'. "
                "Use 'gemini' or 'whisper'."
            ),
        )

    if not full_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{provider} returned an empty transcript.",
        )

    return TranscriptionResponse(
        episode_id=episode_id,
        media_file_id=media_file_id,
        transcript=full_text,
        segments=segments,
        provider=provider,
    )
