"""
Gemini API wrapper.

Wraps google-generativeai so the rest of the app only ever deals with a
validated AnalysisResult object, never raw model output. Handles prompt
construction, JSON extraction, and error translation into HTTPException
so callers in the API layer can simply let exceptions propagate.
"""
import json
import logging
import re

import google.generativeai as genai
from fastapi import HTTPException, status

from app.config import get_settings
from app.schemas.episode import AnalysisResult

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT_TEMPLATE = """You are an expert podcast editor. Analyze the \
following podcast transcript and identify editorial opportunities.

Return ONLY a single JSON object (no markdown fences, no commentary) with \
exactly this shape:

{{
  "strong_moments": [
    {{"timestamp": <seconds:float>, "description": <string>, "confidence": <0.0-1.0 float>}}
  ],
  "weak_sections": [
    {{"start": <seconds:float>, "end": <seconds:float>, "reason": <string>}}
  ],
  "clip_candidates": [
    {{"start": <seconds:float>, "end": <seconds:float>, "hook": <string>}}
  ],
  "opening_candidate": {{"timestamp": <seconds:float>, "description": <string>}} or null,
  "closing_candidate": {{"timestamp": <seconds:float>, "description": <string>}} or null
}}

Guidance:
- "strong_moments" are individual high-value beats worth highlighting (great \
quotes, insights, humor, emotional peaks).
- "weak_sections" are spans that drag, ramble, or should be considered for \
cutting.
- "clip_candidates" are self-contained spans (typically 15-90 seconds) \
suitable for standalone social clips, each with a short "hook" describing \
why it would grab attention.
- "opening_candidate" is the strongest moment to use as the episode's cold \
open, if one exists.
- "closing_candidate" is the strongest moment to end the episode on, if one \
exists.
- If the transcript includes timestamps, use them. If not, estimate seconds \
from position in the text assuming natural speaking pace.
- If a category has no good candidates, return an empty list (or null for \
opening/closing candidate).

Transcript:
\"\"\"
{transcript}
\"\"\"
"""

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class GeminiService:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._model_name = settings.gemini_model
        self._configured = False

    def _ensure_configured(self) -> None:
        if self._configured:
            return
        if not self._api_key or self._api_key == "your-key-here":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "GEMINI_API_KEY is not configured. Set it in your "
                    "environment before calling the analysis endpoint."
                ),
            )
        genai.configure(api_key=self._api_key)
        self._configured = True

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        return _JSON_FENCE_RE.sub("", text.strip()).strip()

    def analyze_transcript(self, transcript: str) -> AnalysisResult:
        """Send a transcript to Gemini and return a validated
        AnalysisResult. Raises HTTPException on any failure so the API
        layer can return a clean error to the client."""
        self._ensure_configured()

        model = genai.GenerativeModel(self._model_name)
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(transcript=transcript)

        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
            )
        except Exception as exc:  # noqa: BLE001 - surface as clean 502
            logger.exception("Gemini API call failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini API request failed: {exc}",
            ) from exc

        raw_text = getattr(response, "text", None)
        if not raw_text:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned an empty response.",
            )

        cleaned = self._strip_code_fence(raw_text)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini response as JSON: %s", cleaned)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned a response that could not be parsed as JSON.",
            ) from exc

        try:
            return AnalysisResult.model_validate(payload)
        except Exception as exc:  # noqa: BLE001 - pydantic ValidationError etc.
            logger.error("Gemini response failed schema validation: %s", payload)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini response did not match the expected schema: {exc}",
            ) from exc


def get_gemini_service() -> GeminiService:
    return GeminiService()
