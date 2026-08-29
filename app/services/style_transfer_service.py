"""
Style transfer suggestion service.

Important honesty note: this does NOT run neural style transfer. Gemini's
vision model compares a reference image against a frame from the episode
and returns a small set of conventional grading parameters (brightness,
contrast, saturation, gamma, temperature, tint) plus a short rationale.
Those parameters are then applied mechanically via ffmpeg (see
color_service.apply_style_params). This keeps the "AI" part limited to
what a vision-language model can actually do well — describing a look in
terms of adjustable parameters — rather than claiming pixel-level style
transfer that Gemini's API doesn't provide.
"""
import json
import logging
import re
from pathlib import Path

import google.generativeai as genai
from fastapi import HTTPException, status
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

STYLE_TRANSFER_PROMPT = """You are a professional colorist. You are shown \
two images: the first is a REFERENCE look the editor wants to match; the \
second is a FRAME from their own footage.

Compare them and suggest grading parameters that would push the footage \
frame toward the reference look. Return ONLY a JSON object (no markdown \
fences, no commentary) with exactly this shape:

{
  "brightness": <float, -1.0 to 1.0, 0 = no change>,
  "contrast": <float, 0.0 to 2.0, 1.0 = no change>,
  "saturation": <float, 0.0 to 3.0, 1.0 = no change>,
  "gamma": <float, 0.1 to 3.0, 1.0 = no change>,
  "temperature": <float, -1.0 (cooler/blue) to 1.0 (warmer/orange), 0 = no change>,
  "tint": <float, -1.0 (green) to 1.0 (magenta), 0 = no change>,
  "rationale": <string, 1-2 sentences explaining the suggested shift>
}

Keep the suggestion conservative and realistic for a single-pass color
correction — this is not a creative license to produce extreme values
unless the reference image is dramatically different from the source
frame.
"""


def _strip_code_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def suggest_grading_params(reference_image_path: Path, frame_path: Path) -> dict:
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your-key-here":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured.",
        )
    genai.configure(api_key=settings.gemini_api_key)

    try:
        reference_img = Image.open(reference_image_path)
        frame_img = Image.open(frame_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read one of the images: {exc}",
        ) from exc

    model = genai.GenerativeModel(settings.gemini_vision_model)
    try:
        response = model.generate_content(
            [STYLE_TRANSFER_PROMPT, reference_img, frame_img],
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini style-transfer suggestion request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini request failed: {exc}",
        ) from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini returned an empty response.",
        )

    cleaned = _strip_code_fence(raw_text)
    try:
        params = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini style-transfer response: %s", cleaned)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini response did not match the expected schema.",
        ) from exc

    return params
