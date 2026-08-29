"""
PR module service.

See app/models/press.py for the framing on journalist leads. Quotes in
the press kit are pulled from the episode's own transcript around each
accepted strong moment's timestamp — real excerpts of the show's own
content, not fabricated. Bios are explicitly framed to the model (and in
the API response) as editable drafts, since PULSE has no real biographical
data about hosts/guests beyond what's in the transcript.
"""
import json
import logging
import re

import google.generativeai as genai
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_MAX_TRANSCRIPT_CHARS = 15000


def _strip_code_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _require_gemini():
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your-key-here":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured.",
        )
    genai.configure(api_key=settings.gemini_api_key)
    return settings


def _call_gemini_json(prompt: str, temperature: float = 0.5) -> dict:
    settings = _require_gemini()
    model = genai.GenerativeModel(settings.gemini_model)
    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": temperature, "response_mime_type": "application/json"},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini request failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini request failed: {exc}") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Gemini returned an empty response.")
    try:
        return json.loads(_strip_code_fence(raw_text))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini response: %s", raw_text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Gemini response did not match the expected schema."
        ) from exc


PRESS_KIT_PROMPT = """You are a podcast publicist. Using the episode title \
and transcript below, write a press kit.

EPISODE TITLE: {title}

TRANSCRIPT (may be truncated):
\"\"\"
{transcript}
\"\"\"

Return ONLY a JSON object (no markdown fences, no commentary) with exactly \
this shape:

{{
  "press_release": <string, 3-5 paragraphs, third person, AP-style>,
  "synopsis_100": <string, ~100 words>,
  "synopsis_250": <string, ~250 words>,
  "synopsis_500": <string, ~500 words>,
  "bios": [
    {{"name": <string, e.g. "Host" if no name is known>, "bio": <string, 2-3 sentences>}}
  ],
  "faq": [
    {{"question": <string>, "answer": <string>}}
    ... 5 to 8 of these, covering what a journalist would likely ask
  ]
}}

Since you don't have verified biographical facts about the real people \
involved, write bios as reasonable drafts clearly meant for a human to \
fact-check and personalize, not as verified claims.
"""


def generate_press_kit_content(episode_title: str, transcript: str) -> dict:
    prompt = PRESS_KIT_PROMPT.format(title=episode_title, transcript=(transcript or "")[:_MAX_TRANSCRIPT_CHARS])
    return _call_gemini_json(prompt, temperature=0.5)


def extract_quotes(transcript_segments: list, accepted_strong_moments: list, window: float = 8.0) -> list:
    """Pull real transcript text around each accepted strong moment's
    timestamp, rather than having an LLM invent quotes."""
    quotes = []
    for review in accepted_strong_moments:
        ts = float((review.decision_reference or {}).get("timestamp", 0.0))
        nearby = [
            seg["text"]
            for seg in (transcript_segments or [])
            if seg.get("start", 0) >= ts - 1 and seg.get("start", 0) <= ts + window
        ]
        text = " ".join(nearby).strip()
        if not text:
            text = (review.decision_reference or {}).get("description", "")
        quotes.append({"text": text, "timestamp": ts, "review_id": review.id})
    return quotes


JOURNALIST_SUGGESTIONS_PROMPT = """You are a PR strategist. Based on this \
podcast episode's topic, suggest the TYPES of outlets and beats (not named \
individuals — you don't have a real, current journalist database, and \
inventing names would just be guessing) that would plausibly be interested \
in covering it.

EPISODE TITLE: {title}

TRANSCRIPT EXCERPT:
\"\"\"
{transcript}
\"\"\"

Return ONLY a JSON object (no markdown fences, no commentary):

{{
  "suggestions": [
    {{
      "outlet_type": <string, e.g. "Tech industry newsletter">,
      "beat": <string, e.g. "AI and creator tools">,
      "why_relevant": <string, 1 sentence>,
      "search_tip": <string, e.g. a search query or directory to find real journalists on this beat>
    }}
    ... 5 to 8 of these
  ]
}}
"""


def generate_journalist_suggestions(episode_title: str, transcript: str) -> list[dict]:
    prompt = JOURNALIST_SUGGESTIONS_PROMPT.format(
        title=episode_title, transcript=(transcript or "")[:_MAX_TRANSCRIPT_CHARS]
    )
    data = _call_gemini_json(prompt, temperature=0.6)
    return data.get("suggestions", [])


PITCH_PROMPT = """Write a short, personalized pitch email (not a subject \
line, just the body, 3 short paragraphs max) from a podcast team to a \
journalist, pitching this episode for coverage.

EPISODE PRESS RELEASE (for context):
\"\"\"
{press_release}
\"\"\"

JOURNALIST NOTES (may be sparse — the user filled these in themselves):
outlet: {outlet}
beat: {beat}
notes: {notes}

Keep it concise, specific to their beat if known, and not generic \
boilerplate. Return ONLY the pitch text, no subject line, no markdown, no \
commentary.
"""


def draft_pitch(press_release: str, outlet: str | None, beat: str | None, notes: str | None) -> str:
    settings = _require_gemini()
    model = genai.GenerativeModel(settings.gemini_model)
    prompt = PITCH_PROMPT.format(
        press_release=press_release[:4000],
        outlet=outlet or "(unknown)",
        beat=beat or "(unknown)",
        notes=notes or "(none)",
    )
    try:
        response = model.generate_content(prompt, generation_config={"temperature": 0.6})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini pitch drafting failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini request failed: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Gemini returned an empty pitch.")
    return text.strip()
