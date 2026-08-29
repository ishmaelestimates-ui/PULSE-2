"""
Postiz API client.

Grounded in Postiz's real public API (https://docs.postiz.com/public-api):
  - Base URL: https://api.postiz.com/public/v1 (hosted) or
    {your-backend-url}/public/v1 (self-hosted)
  - Auth header: `Authorization: {api_key}` — no "Bearer" prefix
  - GET  /integrations           list connected channels
  - GET  /posts?from=&to=        list posts in a date range
  - POST /posts                  create/schedule a post:
        {"type": "now"|"schedule"|"draft", "date": "...", "posts": [...], "tags": [...]}
  - DELETE /posts/:id
  - POST /upload, /upload-from-url

Two things this integration can't fully verify without a live Postiz
instance and its post-creation wizard: (1) the exact per-platform
`settings` payload shape inside each post object (each platform has its
own schema, e.g. Reddit's subreddit/flair fields) — the wizard in the
Postiz UI is the authoritative source for that, so treat the payload
builder here as a reasonable starting point to verify against a live
instance, not a guarantee; (2) whether analytics/engagement-metrics are
exposed on this exact endpoint set for self-hosted instances — if not,
`get_post_status` degrades gracefully to "unknown" rather than failing.
"""
import logging

import httpx
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)


def _require_configured() -> tuple[str, str]:
    settings = get_settings()
    if not settings.postiz_api_key or settings.postiz_api_key == "your-key-here":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="POSTIZ_API_KEY is not configured.",
        )
    base_url = settings.postiz_url.rstrip("/")
    if not base_url.endswith("/public/v1"):
        base_url = f"{base_url}/public/v1"
    return base_url, settings.postiz_api_key


def _client(base_url: str, api_key: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        timeout=30.0,
    )


def _handle_error(exc: httpx.HTTPStatusError) -> None:
    detail = exc.response.text[:500] if exc.response is not None else str(exc)
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Postiz API error ({exc.response.status_code if exc.response else '?'}): {detail}",
    ) from exc


def list_integrations() -> list[dict]:
    base_url, api_key = _require_configured()
    try:
        with _client(base_url, api_key) as client:
            resp = client.get("/integrations")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        _handle_error(exc)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Postiz at {base_url}: {exc}",
        ) from exc


def create_post(
    integration_id: str, content_text: str, post_type: str = "schedule", scheduled_iso: str | None = None
) -> dict:
    """Create/schedule a post on one channel. `post_type` is "now",
    "schedule", or "draft" per the Postiz API."""
    base_url, api_key = _require_configured()
    payload = {
        "type": post_type,
        "date": scheduled_iso,
        "posts": [
            {
                "integration": {"id": integration_id},
                "content": content_text,
            }
        ],
        "tags": [],
    }
    try:
        with _client(base_url, api_key) as client:
            resp = client.post("/posts", json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        _handle_error(exc)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Postiz at {base_url}: {exc}",
        ) from exc


def get_post_status(postiz_post_id: str) -> dict:
    """Best-effort status/engagement lookup. Postiz's exact analytics
    surface for self-hosted instances isn't fully confirmed here — if the
    lookup fails, this returns an "unknown" status rather than raising,
    so a flaky/absent analytics endpoint doesn't break the whole page."""
    base_url, api_key = _require_configured()
    try:
        with _client(base_url, api_key) as client:
            resp = client.get(f"/posts/{postiz_post_id}")
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.warning("Postiz status lookup failed for %s: %s", postiz_post_id, exc)
        return {"status": "unknown", "error": str(exc)}


def delete_post(postiz_post_id: str) -> None:
    base_url, api_key = _require_configured()
    try:
        with _client(base_url, api_key) as client:
            resp = client.delete(f"/posts/{postiz_post_id}")
            # Per Postiz docs: 404 on delete means "already deleted", safe to ignore.
            if resp.status_code not in (200, 204, 404):
                resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _handle_error(exc)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Postiz at {base_url}: {exc}",
        ) from exc
