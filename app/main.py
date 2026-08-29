"""
PULSE backend — FastAPI application entrypoint.

Wires up the episode, analysis, review, and media routers; mounts media
storage for static serving; and exposes a health check for container
orchestration / load balancer probes.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    analysis,
    auth,
    brand_settings,
    campaign,
    color,
    dashboard,
    distribution,
    episodes,
    fame,
    film,
    media,
    press,
    reddit,
    reviews,
    users,
)
from app.config import get_settings
from app.database import SessionLocal
from app.services import auth_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="PULSE",
    description="Podcast production and distribution system backend.",
    version="0.8.0",
)

# Permissive CORS for MVP/local development. Tighten allow_origins before
# deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(episodes.router)
app.include_router(analysis.router)
app.include_router(reviews.router)
app.include_router(media.router)
app.include_router(color.router)
app.include_router(brand_settings.router)
app.include_router(campaign.router)
app.include_router(press.router)
app.include_router(reddit.router)
app.include_router(distribution.router)
app.include_router(film.router)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(fame.router)


@app.on_event("startup")
def bootstrap_admin():
    """Creates the first admin user if none exists yet. See
    app/services/auth_service.py — the generated password (if
    BOOTSTRAP_ADMIN_PASSWORD isn't set) is printed to the server log
    exactly once and is not recoverable after that."""
    db = SessionLocal()
    try:
        auth_service.bootstrap_admin_if_needed(db)
    finally:
        db.close()

# Serve uploaded/derived media files. Layout under MEDIA_STORAGE_PATH is
# `uploads/{episode_id}/{filename}` (originals), `derived/{episode_id}/
# {filename}` (ffmpeg-extracted audio, thumbnails, color-grade previews),
# and `brand/{filename}` (logo, intro/outro music), so a file ends up
# reachable at e.g. `/media/uploads/3/abc123.mp4`.
media_root = Path(settings.media_storage_path)
media_root.mkdir(parents=True, exist_ok=True)
(media_root / "uploads").mkdir(parents=True, exist_ok=True)
(media_root / "derived").mkdir(parents=True, exist_ok=True)
(media_root / "brand").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_root)), name="media")


@app.exception_handler(HTTPException)
async def log_http_exceptions(request, exc: HTTPException):
    """Log HTTPExceptions before delegating to the default handler, so
    4xx/5xx responses are visible in server logs."""
    logger.warning("HTTPException %s at %s: %s", exc.status_code, request.url, exc.detail)
    return await http_exception_handler(request, exc)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "environment": settings.environment}


@app.get("/", tags=["health"])
def root():
    return {"service": "PULSE backend", "docs": "/docs"}
