"""
Fame module service.

See app/models/fame.py for the full honesty framing. In short: PULSE
cannot measure real-world fame, so `compute_fame_score` is a transparent,
deterministic formula over PULSE's own real tracked numbers — not a
claim about the outside world. The exact formula is documented here and
echoed in the API response so it's inspectable, not a black box.

Sentiment classification on a given text snippet, by contrast, IS a
legitimate thing an LLM can do well — that part uses Gemini for real.
"""
import json
import logging
import math
import re

import google.generativeai as genai
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

FAME_SCORE_FORMULA_NOTE = (
    "Deterministic composite of PULSE's own tracked data — not a real-world "
    "fame/authority measurement. engagement = log-scaled Reddit upvotes+comments "
    "and campaign acceptance; reach_proxy = coverage count + festival submissions; "
    "authority_proxy = accepted festival tier + completed milestones; momentum = "
    "change vs. the previous snapshot. Weighted 40/25/20/15."
)


def _strip_code_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _log_scale(raw: float, scale: float = 20.0) -> float:
    return min(100.0, scale * math.log1p(max(0.0, raw)))


def compute_fame_score(
    reddit_posts: list,
    accepted_review_count: int,
    coverage_count: int,
    festival_matches: list,
    milestones_done: int,
    previous_score: float | None,
) -> dict:
    engagement_raw = sum((p.upvotes + p.comment_count) for p in reddit_posts) + (accepted_review_count * 2)
    engagement = _log_scale(engagement_raw)

    submitted_or_accepted = sum(1 for f in festival_matches if f.status in ("submitted", "accepted"))
    reach_proxy = min(100.0, coverage_count * 15 + submitted_or_accepted * 10)

    authority_raw = sum(20 for f in festival_matches if f.tier == 1 and f.status == "accepted")
    authority_raw += sum(10 for f in festival_matches if f.tier == 2 and f.status == "accepted")
    authority_raw += milestones_done * 3
    authority_proxy = min(100.0, authority_raw)

    current_raw_total = engagement + reach_proxy + authority_proxy
    if previous_score is None:
        momentum = 50.0  # neutral — no history to compare against yet
    else:
        delta = current_raw_total - previous_score
        momentum = max(0.0, min(100.0, 50.0 + delta))

    score = round(engagement * 0.40 + reach_proxy * 0.25 + authority_proxy * 0.20 + momentum * 0.15, 1)

    return {
        "score": score,
        "components": {
            "engagement": round(engagement, 1),
            "reach_proxy": round(reach_proxy, 1),
            "authority_proxy": round(authority_proxy, 1),
            "momentum": round(momentum, 1),
        },
    }


def project_score(history: list[tuple], horizon_days: int) -> dict:
    """Naive linear regression over (days_since_first, score) points.
    NOT a real-world forecast — a mechanical extrapolation of PULSE's own
    internal index, stated as such in the API response."""
    if len(history) < 2:
        current = history[-1][1] if history else 0.0
        return {"projected_score": current, "confidence": "insufficient_history"}

    xs = [h[0] for h in history]
    ys = [h[1] for h in history]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs) or 1.0
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x

    projected_x = xs[-1] + horizon_days
    projected = slope * projected_x + intercept
    projected = max(0.0, min(100.0, projected))

    return {"projected_score": round(projected, 1), "confidence": "naive_linear_trend"}


SENTIMENT_PROMPT = """Classify the sentiment of this text snippet toward its \
subject as exactly one of: positive, negative, neutral.

TEXT:
\"\"\"
{text}
\"\"\"

Return ONLY a JSON object: {{"sentiment": "positive"|"negative"|"neutral"}}
"""


def classify_sentiment(text: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your-key-here":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GEMINI_API_KEY is not configured.")
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    prompt = SENTIMENT_PROMPT.format(text=text[:2000])
    try:
        response = model.generate_content(
            prompt, generation_config={"temperature": 0.0, "response_mime_type": "application/json"}
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini sentiment classification failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini request failed: {exc}") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Gemini returned an empty response.")
    try:
        data = json.loads(_strip_code_fence(raw_text))
        sentiment = data.get("sentiment", "neutral")
        return sentiment if sentiment in ("positive", "negative", "neutral") else "neutral"
    except json.JSONDecodeError:
        return "neutral"
