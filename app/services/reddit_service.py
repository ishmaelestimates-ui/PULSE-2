"""
Reddit distribution service.

Subreddit search/analysis calls Reddit's public read-only JSON API
directly (no OAuth needed for these particular endpoints — just a
descriptive User-Agent, which Reddit requires). Post generation uses
Gemini, but explicitly for genuinely-curious titles and a disclosed post
body — see app/models/reddit.py for why "frame as organic discussion, no
self-promotion" was not implemented as specified.
"""
import json
import logging
import re

import google.generativeai as genai
import httpx
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_MAX_TRANSCRIPT_CHARS = 8000
REDDIT_BASE = "https://www.reddit.com"

DISCLOSURE_NOTE = "Posted by the show's creator — full disclosure, not an outside recommendation."


def _strip_code_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _reddit_headers() -> dict:
    settings = get_settings()
    return {"User-Agent": settings.reddit_user_agent}


def search_subreddits(query: str, limit: int = 10) -> list[dict]:
    """Real search against Reddit's public API — no OAuth required for
    this endpoint, just a proper User-Agent."""
    try:
        resp = httpx.get(
            f"{REDDIT_BASE}/subreddits/search.json",
            params={"q": query, "limit": limit},
            headers=_reddit_headers(),
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Reddit search failed ({exc.response.status_code}): {exc.response.text[:300]}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not reach Reddit: {exc}"
        ) from exc

    results = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        results.append(
            {
                "name": d.get("display_name_prefixed", d.get("display_name", "")),
                "subscribers": d.get("subscribers"),
                "active_users": d.get("accounts_active"),
                "description": (d.get("public_description") or "").strip() or None,
                "over_18": bool(d.get("over18")),
            }
        )
    return results


def analyze_subreddit(name: str) -> dict:
    name = name.lstrip("r/").strip("/")
    headers = _reddit_headers()

    try:
        about = httpx.get(f"{REDDIT_BASE}/r/{name}/about.json", headers=headers, timeout=15.0)
        about.raise_for_status()
        about_data = about.json().get("data", {})
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Subreddit r/{name} not found or private."
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not reach Reddit: {exc}") from exc

    rules_summary: list[str] = []
    try:
        rules_resp = httpx.get(f"{REDDIT_BASE}/r/{name}/about/rules.json", headers=headers, timeout=15.0)
        if rules_resp.status_code == 200:
            for rule in rules_resp.json().get("rules", []):
                short = rule.get("short_name") or rule.get("violation_reason")
                if short:
                    rules_summary.append(short)
    except httpx.RequestError:
        pass  # rules are a nice-to-have, don't fail the whole analysis

    top_posts: list[dict] = []
    try:
        hot_resp = httpx.get(
            f"{REDDIT_BASE}/r/{name}/hot.json", params={"limit": 5}, headers=headers, timeout=15.0
        )
        if hot_resp.status_code == 200:
            for child in hot_resp.json().get("data", {}).get("children", []):
                d = child.get("data", {})
                top_posts.append(
                    {
                        "title": d.get("title"),
                        "score": d.get("score"),
                        "num_comments": d.get("num_comments"),
                        "flair": d.get("link_flair_text"),
                    }
                )
    except httpx.RequestError:
        pass

    return {
        "name": f"r/{name}",
        "subscribers": about_data.get("subscribers"),
        "active_users": about_data.get("accounts_active"),
        "description": (about_data.get("public_description") or "").strip() or None,
        "rules_summary": rules_summary,
        "top_posts": top_posts,
    }


REDDIT_GENERATE_PROMPT = """You are helping a podcast creator write a \
Reddit post to share their own episode, TRANSPARENTLY. This is self-
promotion and must read like it: the post should disclose that the \
poster made the show, while still being genuinely interesting rather than \
like an ad.

EPISODE TITLE: {title}

TRANSCRIPT EXCERPT:
\"\"\"
{transcript}
\"\"\"

Return ONLY a JSON object (no markdown fences, no commentary):

{{
  "title_options": [<string>, ... 5 to 10 titles, curiosity-driven but honest, not clickbait>],
  "body": <string, 2-3 short paragraphs. Open by disclosing you made this podcast. Explain what's genuinely interesting about it. Do not pretend to be a disinterested third party.>,
  "flair_suggestions": [<string>, ... 2-4 plausible flair names>],
  "topic_keywords": [<string>, ... 3-6 short keywords/phrases to search Reddit for relevant subreddits>]
}}
"""


def generate_reddit_post_content(episode_title: str, transcript: str) -> dict:
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your-key-here":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GEMINI_API_KEY is not configured.")
    genai.configure(api_key=settings.gemini_api_key)

    prompt = REDDIT_GENERATE_PROMPT.format(title=episode_title, transcript=(transcript or "")[:_MAX_TRANSCRIPT_CHARS])
    model = genai.GenerativeModel(settings.gemini_model)
    try:
        response = model.generate_content(
            prompt, generation_config={"temperature": 0.6, "response_mime_type": "application/json"}
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini Reddit generation failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini request failed: {exc}") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Gemini returned an empty response.")
    try:
        return json.loads(_strip_code_fence(raw_text))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Gemini response did not match the expected schema."
        ) from exc


def recommend_subreddits(topic_keywords: list[str], max_results: int = 10) -> list[dict]:
    """Real subreddit candidates, found by searching Reddit for each
    Gemini-suggested keyword — not hallucinated subreddit names."""
    seen = {}
    for keyword in topic_keywords:
        try:
            for result in search_subreddits(keyword, limit=5):
                seen.setdefault(result["name"], result)
        except HTTPException:
            continue
        if len(seen) >= max_results:
            break
    return list(seen.values())[:max_results]


COMMENT_REPLY_PROMPT = """You are drafting a reply for a podcast creator \
to post themselves (in their own disclosed voice) to a comment on their \
Reddit post.

EPISODE CONTEXT: {context}

COMMENT TO REPLY TO:
\"\"\"
{comment}
\"\"\"

Write a genuine, specific reply (2-4 sentences) — not generic thanks, not \
a sales pitch. Return ONLY the reply text, no commentary.
"""


def suggest_comment_reply(comment_body: str, episode_context: str | None) -> str:
    settings = get_settings()
    if not settings.gemini_api_key or settings.gemini_api_key == "your-key-here":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GEMINI_API_KEY is not configured.")
    genai.configure(api_key=settings.gemini_api_key)

    prompt = COMMENT_REPLY_PROMPT.format(context=episode_context or "(a podcast episode)", comment=comment_body[:2000])
    model = genai.GenerativeModel(settings.gemini_model)
    try:
        response = model.generate_content(prompt, generation_config={"temperature": 0.6})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini comment-reply suggestion failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini request failed: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Gemini returned an empty reply.")
    return text.strip()


def search_mentions(query: str, limit: int = 15) -> list[dict]:
    """Real, site-wide Reddit search (posts) for a name/brand — used by
    the Fame module's media monitoring. Reddit only; no other platform is
    searched (no API access to Twitter/X, news sites, etc. in this app)."""
    try:
        resp = httpx.get(
            f"{REDDIT_BASE}/search.json",
            params={"q": query, "limit": limit, "sort": "new"},
            headers=_reddit_headers(),
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Reddit search failed ({exc.response.status_code}): {exc.response.text[:300]}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not reach Reddit: {exc}") from exc

    results = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        results.append(
            {
                "platform": f"reddit (r/{d.get('subreddit', '')})",
                "url": f"{REDDIT_BASE}{d.get('permalink', '')}" if d.get("permalink") else None,
                "excerpt": (d.get("title") or "") + ((" — " + d["selftext"][:200]) if d.get("selftext") else ""),
                "author": d.get("author"),
            }
        )
    return results
