"""
Film features service.

Honesty framing (see schemas/film.py for the response-level notes users
actually see):
  - Acts: Gemini's narrative-arc read, with its own confidence score.
    Starting point for an editor, not a fact about the content.
  - Trailer cut selection is DETERMINISTIC — ranked by confidence + hype
    score (when available), packed to fit each target duration. Only
    `scene_type` (used for CSV marker coloring) comes from Gemini, and
    it's an explicitly qualitative tone read, not a factual category.
  - Festival matches: Gemini can name real, well-known festivals
    correctly, but deadlines/fees are guesses from stale training data.
    Every match starts unverified.
  - Sync-licensing report: a plain keyword/LLM heuristic scan of your own
    transcript for third-party content mentions. Not legal advice, not
    exhaustive, not a clearance.
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


def _call_gemini_json(prompt: str, temperature: float = 0.4) -> dict:
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your-key-here":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GEMINI_API_KEY is not configured.")
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    try:
        response = model.generate_content(
            prompt, generation_config={"temperature": temperature, "response_mime_type": "application/json"}
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


# --------------------------------------------------------------------------
# Acts
# --------------------------------------------------------------------------
ACTS_PROMPT = """You are a story editor. Analyze this transcript for a \
3-act narrative structure (Setup, Confrontation, Resolution) — even if it's \
a podcast conversation rather than a scripted film, look for where the \
framing/stakes are set up, where the core tension or exploration develops, \
and where it resolves or lands.

TRANSCRIPT (may be truncated):
\"\"\"
{transcript}
\"\"\"

Return ONLY a JSON object (no markdown fences, no commentary):

{{
  "acts": [
    {{"act_number": 1, "title": "Setup", "start_time": <seconds:float>, "end_time": <seconds:float>, "description": <string>, "confidence": <0.0-1.0 float>}},
    {{"act_number": 2, "title": "Confrontation", "start_time": <seconds:float>, "end_time": <seconds:float>, "description": <string>, "confidence": <0.0-1.0 float>}},
    {{"act_number": 3, "title": "Resolution", "start_time": <seconds:float>, "end_time": <seconds:float>, "description": <string>, "confidence": <0.0-1.0 float>}}
  ]
}}

If the transcript has timestamps, use them. If not, estimate from position \
in the text at a natural speaking pace. Be honest in your confidence scores \
— a loosely-structured conversation should get lower confidence than a \
tightly-plotted narrative.
"""


def detect_acts(transcript: str) -> list[dict]:
    prompt = ACTS_PROMPT.format(transcript=(transcript or "")[:_MAX_TRANSCRIPT_CHARS])
    data = _call_gemini_json(prompt, temperature=0.3)
    return data.get("acts", [])


# --------------------------------------------------------------------------
# Trailer cut lists (deterministic selection, AI only for scene_type)
# --------------------------------------------------------------------------
def _span_confidence_label(review, hype_map: dict) -> tuple[float, float, float, str]:
    ref = review.decision_reference or {}
    if "start" in ref and "end" in ref:
        start, end = float(ref["start"]), float(ref["end"])
    else:
        t = float(ref.get("timestamp", 0.0))
        start, end = t, t + 4.0
    base_confidence = float(ref.get("confidence", 0.5))
    hype = hype_map.get(review.id, {}).get("score")
    # Blend confidence (0-1) with hype score (0-100) if we have it,
    # otherwise fall back to confidence alone. Deterministic combination.
    combined = (base_confidence * 0.6) + ((hype / 100) * 0.4) if hype is not None else base_confidence
    label = ref.get("description") or ref.get("hook") or ""
    return start, end, combined, label


def build_trailer_cut(accepted_reviews: list, hype_map: dict, target_seconds: float) -> list[dict]:
    candidates = [
        (review, *_span_confidence_label(review, hype_map))
        for review in accepted_reviews
        if review.decision_type in ("strong_moment", "clip_candidate")
    ]
    candidates.sort(key=lambda c: c[3], reverse=True)

    selected = []
    total = 0.0
    for review, start, end, score, label in candidates:
        duration = max(0.5, end - start)
        if total + duration > target_seconds and selected:
            continue
        selected.append({"review_id": review.id, "start": start, "end": end, "label": label})
        total += duration
        if total >= target_seconds:
            break

    selected.sort(key=lambda c: c["start"])
    return selected


SCENE_TYPE_PROMPT = """Classify the qualitative TONE of each of these clip \
descriptions into exactly one of: Action, Dialogue, Emotional, Climax. This \
is a subjective read for organizing a trailer edit, not a factual category.

CLIPS:
{clips}

Return ONLY a JSON object: {{"labels": [<string>, ...]}} with one label per \
clip, in the same order.
"""


def classify_scene_types(descriptions: list[str]) -> list[str]:
    if not descriptions:
        return []
    clips_text = "\n".join(f"{i+1}. {d}" for i, d in enumerate(descriptions))
    prompt = SCENE_TYPE_PROMPT.format(clips=clips_text)
    try:
        data = _call_gemini_json(prompt, temperature=0.2)
        labels = data.get("labels", [])
        if len(labels) == len(descriptions):
            return labels
    except HTTPException:
        pass
    return ["Dialogue"] * len(descriptions)  # safe fallback, doesn't block the feature


# --------------------------------------------------------------------------
# Festivals
# --------------------------------------------------------------------------
FESTIVAL_PROMPT = """You are a film festival strategist. Based on this \
episode/film's topic and tone, suggest festivals that would plausibly be a \
good fit.

TITLE: {title}
TRANSCRIPT EXCERPT:
\"\"\"
{transcript}
\"\"\"

Tier definitions: Tier 1 = Cannes/Sundance/TIFF/Berlin-level; Tier 2 = \
SXSW/Tribeca/Venice-level; Tier 3 = regional/genre-specific festivals.

Return ONLY a JSON object (no markdown fences, no commentary):

{{
  "matches": [
    {{
      "festival_name": <string, real festival name>,
      "tier": <1, 2, or 3>,
      "why_relevant": <string, 1 sentence>,
      "deadline_guess": <string, e.g. "Typically early January" — approximate, may be wrong, or null if unsure>,
      "entry_fee_guess": <string, e.g. "~$75-100 (varies by deadline tier)" or null if unsure>
    }}
    ... 5 to 8 of these, mixing tiers
  ]
}}

Be conservative — only suggest tier 1/2 if there's a genuine plausible fit, \
not just because they're famous.
"""


def suggest_festivals(episode_title: str, transcript: str) -> list[dict]:
    prompt = FESTIVAL_PROMPT.format(title=episode_title, transcript=(transcript or "")[:_MAX_TRANSCRIPT_CHARS])
    data = _call_gemini_json(prompt, temperature=0.5)
    return data.get("matches", [])


SUBMISSION_PROMPT = """Write a film festival submission package for this \
episode/film.

TITLE: {title}
TRANSCRIPT EXCERPT:
\"\"\"
{transcript}
\"\"\"

Return ONLY a JSON object (no markdown fences, no commentary):

{{
  "logline": <string, one sentence>,
  "synopsis": <string, 150-250 words>,
  "directors_statement": <string, 2-3 paragraphs, first person>,
  "key_art_brief": <string, a written creative brief describing a poster/key-art concept — NOT an image, a description a designer could work from>
}}
"""


def generate_festival_submission(episode_title: str, transcript: str) -> dict:
    prompt = SUBMISSION_PROMPT.format(title=episode_title, transcript=(transcript or "")[:_MAX_TRANSCRIPT_CHARS])
    return _call_gemini_json(prompt, temperature=0.6)


# --------------------------------------------------------------------------
# Sync licensing (heuristic transcript scan)
# --------------------------------------------------------------------------
SYNC_PROMPT = """Scan this transcript for mentions of songs, musicians, \
bands, or other third-party copyrighted media (movie titles, TV shows, \
brand names used in ways that could raise rights questions) that a podcast \
producer should have a human review before wide distribution.

TRANSCRIPT (may be truncated):
\"\"\"
{transcript}
\"\"\"

Return ONLY a JSON object (no markdown fences, no commentary):

{{
  "flags": [
    {{
      "excerpt": <string, the relevant snippet, kept short>,
      "concern_type": <one of: "music_mention", "third_party_content", "other">,
      "recommended_action": <string, e.g. "Confirm no copyrighted audio was played during this section">
    }}
  ]
}}

Only flag genuine potential concerns (e.g. a song was played or performed, \
not just casually mentioned in passing conversation — though borderline \
cases are fine to include with a lower-key recommended_action). If there's \
nothing worth flagging, return an empty list.
"""


def scan_sync_licensing(transcript: str) -> list[dict]:
    prompt = SYNC_PROMPT.format(transcript=(transcript or "")[:_MAX_TRANSCRIPT_CHARS])
    data = _call_gemini_json(prompt, temperature=0.2)
    return data.get("flags", [])
