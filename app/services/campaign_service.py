"""
Campaign generation service.

Honesty framing, stated once here rather than scattered as comments:

  - Social posts, hooks, press blurb, newsletter, and show notes are
    ordinary text generation — Gemini writing marketing copy from the
    transcript and accepted editorial decisions. Nothing speculative
    about that part.
  - Hype scores and viral predictions are NOT measured engagement data
    and there is no trained predictive model behind them. They're
    Gemini's qualitative read of each clip (does the hook create
    curiosity, is there an emotional beat, does it stand alone without
    context) turned into a number/label. Both the API response and the
    UI carry an explicit disclaimer saying so — this is a second opinion
    for the editor to weigh, not a forecast.
  - The release schedule's "best times per platform" are generic,
    commonly-cited industry defaults (not derived from this show's own
    audience — PULSE has no analytics/social integration to draw real
    data from). Dates are just today + N days, evenly staggered.
  - The trailer cut list is NOT Gemini's output — it's assembled
    deterministically in Python from the accepted strong moments/clips
    with the highest confidence scores, greedily packed to fit a ~60s
    budget. Deterministic and reproducible on purpose.
"""
import json
import logging
import re
from datetime import datetime, timedelta, timezone

import google.generativeai as genai
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_MAX_TRANSCRIPT_CHARS = 15000  # keep the prompt within a reasonable size

PLATFORMS = ["tiktok", "youtube", "linkedin", "x", "instagram", "facebook"]

# Generic, commonly-cited "best time to post" windows per platform. Not
# derived from any of this show's actual audience data.
GENERIC_BEST_TIMES = {
    "tiktok": ["6:00 PM", "9:00 PM"],
    "youtube": ["2:00 PM", "8:00 PM (weekends)"],
    "linkedin": ["8:00 AM", "12:00 PM (weekdays)"],
    "x": ["9:00 AM", "12:00 PM", "6:00 PM"],
    "instagram": ["11:00 AM", "7:00 PM"],
    "facebook": ["1:00 PM", "3:00 PM"],
}

CAMPAIGN_PROMPT_TEMPLATE = """You are a podcast marketing strategist. Using \
the episode transcript and the editor's accepted highlights below, generate \
a full marketing campaign.

EPISODE TITLE: {title}

ACCEPTED STRONG MOMENTS (id, timestamp, description):
{strong_moments}

ACCEPTED CLIP CANDIDATES (id, start-end, hook):
{clip_candidates}

TRANSCRIPT (may be truncated):
\"\"\"
{transcript}
\"\"\"

Return ONLY a JSON object (no markdown fences, no commentary) with exactly \
this shape:

{{
  "social_posts": {{
    "tiktok": {{"text": <string, short/punchy>, "hashtags": [<string>, ...]}},
    "youtube": {{"text": <string, can be longer/descriptive>, "hashtags": [<string>, ...]}},
    "linkedin": {{"text": <string, professional tone>, "hashtags": [<string>, ...]}},
    "x": {{"text": <string, under 280 chars>, "hashtags": [<string>, ...]}},
    "instagram": {{"text": <string>, "hashtags": [<string>, ...]}},
    "facebook": {{"text": <string>, "hashtags": [<string>, ...]}}
  }},
  "hooks": [
    {{"review_id": <int from the accepted lists above, or null>, "text": <string, one punchy hook line>, "curiosity_gap_score": <int 1-10>}}
    ... 10 to 15 of these, drawing from the accepted moments/clips above
  ],
  "press_blurb": <string, exactly 3 sentences, third person>,
  "newsletter": {{
    "subject": <string>,
    "preview": <string, the email preview/preheader text>,
    "body": <string, 3-5 short paragraphs>
  }},
  "show_notes": <string, markdown with a one-paragraph summary followed by a timestamped bullet list of the accepted moments>,
  "hype_scores": [
    {{"review_id": <int from the accepted lists above>, "score": <int 1-100>, "rationale": <string, 1 sentence>}}
    ... one entry per accepted strong moment AND clip candidate listed above
  ],
  "viral_predictions": [
    {{"review_id": <int from the accepted lists above>, "platform": <one of: tiktok, youtube, linkedin, x, instagram, facebook>, "label": <one of: viral, high, moderate, low>, "rationale": <string, 1 sentence>}}
    ... one entry per accepted strong moment AND clip candidate listed above, predicting its single best-fit platform
  ]
}}

For hype_scores and viral_predictions: these are your qualitative judgment \
of hook strength, emotional resonance, and shareability — be honest and use \
the full range (not everything is a 90+). Reserve "viral" for something \
genuinely exceptional; most decent clips should land in "moderate" to "high".
"""


def _strip_code_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _format_strong_moments(reviews: list) -> str:
    lines = [
        f"- id={r.id}, t={r.decision_reference.get('timestamp', 0):.0f}s: "
        f"{r.decision_reference.get('description', '')}"
        for r in reviews
        if r.decision_type == "strong_moment"
    ]
    return "\n".join(lines) if lines else "(none accepted)"


def _format_clip_candidates(reviews: list) -> str:
    lines = [
        f"- id={r.id}, {r.decision_reference.get('start', 0):.0f}s-"
        f"{r.decision_reference.get('end', 0):.0f}s: {r.decision_reference.get('hook', '')}"
        for r in reviews
        if r.decision_type == "clip_candidate"
    ]
    return "\n".join(lines) if lines else "(none accepted)"


def generate_campaign_content(
    episode_title: str, transcript: str, accepted_reviews: list
) -> dict:
    """Call Gemini once for all text-generation pieces of the campaign
    (social posts, hooks, press blurb, newsletter, show notes) plus the
    AI-estimated hype scores / viral predictions. Returns a raw dict —
    validated review_id references are checked by the caller since an
    LLM can hallucinate IDs."""
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your-key-here":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured.",
        )
    genai.configure(api_key=settings.gemini_api_key)

    prompt = CAMPAIGN_PROMPT_TEMPLATE.format(
        title=episode_title,
        strong_moments=_format_strong_moments(accepted_reviews),
        clip_candidates=_format_clip_candidates(accepted_reviews),
        transcript=(transcript or "")[:_MAX_TRANSCRIPT_CHARS],
    )

    model = genai.GenerativeModel(settings.gemini_model)
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.6,
                "response_mime_type": "application/json",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini campaign generation failed")
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
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini campaign response: %s", cleaned)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini response did not match the expected schema.",
        ) from exc


def build_schedule(start_date: datetime | None = None) -> dict:
    """Deterministic release schedule: generic best-time-of-day windows
    per platform, plus a staggered set of suggested dates starting today
    (one platform per day, cycling)."""
    start_date = start_date or datetime.now(timezone.utc)
    suggested_dates = []
    for i, platform in enumerate(PLATFORMS):
        post_date = start_date + timedelta(days=i)
        suggested_dates.append(
            {
                "platform": platform,
                "date": post_date.date().isoformat(),
                "suggested_time": GENERIC_BEST_TIMES[platform][0],
            }
        )
    return {
        "generic_best_times": GENERIC_BEST_TIMES,
        "suggested_dates": suggested_dates,
        "note": (
            "Best-time windows are generic industry defaults, not derived "
            "from this show's actual audience data."
        ),
    }


def build_trailer_cutlist(accepted_reviews: list, max_seconds: float = 60.0) -> list:
    """Greedily pack the highest-confidence accepted strong moments /
    clip candidates into a ~60s trailer, preserving chronological order
    in the final cut. Pure Python, deterministic, no LLM involved."""

    def span_and_confidence(review):
        ref = review.decision_reference or {}
        if "start" in ref and "end" in ref:
            start, end = float(ref["start"]), float(ref["end"])
        else:
            t = float(ref.get("timestamp", 0.0))
            start, end = t, t + 4.0  # give point moments a nominal 4s window
        confidence = float(ref.get("confidence", 0.5))
        label = ref.get("description") or ref.get("hook") or ""
        return start, end, confidence, label

    candidates = [
        (review, *span_and_confidence(review))
        for review in accepted_reviews
        if review.decision_type in ("strong_moment", "clip_candidate")
    ]
    # Rank by confidence (highest first) for selection...
    candidates.sort(key=lambda c: c[3], reverse=True)

    selected = []
    total = 0.0
    for review, start, end, confidence, label in candidates:
        duration = max(0.5, end - start)
        if total + duration > max_seconds and selected:
            continue
        selected.append(
            {
                "review_id": review.id,
                "start": start,
                "end": end,
                "label": label,
            }
        )
        total += duration
        if total >= max_seconds:
            break

    # ...but present the final cut in chronological order, like an
    # actual trailer timeline.
    selected.sort(key=lambda c: c["start"])
    return selected
