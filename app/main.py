"""
PULSE backend — FastAPI application entrypoint.

Wires up the episode, analysis, review, and media routers; mounts media
storage for static serving; and exposes a health check for container
orchestration / load balancer probes.
"""
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    analysis,
    audit,
    autosave,
    recovery,
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
from app.api.deps import get_current_user
from app.services import auth_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="PULSE",
    description="Podcast production and distribution system backend.",
    version="0.8.0",
)

# Browser origins are explicit so authenticated requests cannot be made
# from an arbitrary website. The development defaults are localhost-only.
allow_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Every application router below auth is protected at the router boundary.
# Individual admin-only endpoints keep their finer-grained dependencies.
_PRIVATE_ROUTER_DEPENDENCIES = [Depends(get_current_user)]
app.include_router(episodes.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(analysis.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(reviews.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(media.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(color.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(brand_settings.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(campaign.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(press.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(reddit.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(distribution.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(film.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(dashboard.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(auth.router)
app.include_router(users.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(fame.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(autosave.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(recovery.router, dependencies=_PRIVATE_ROUTER_DEPENDENCIES)
app.include_router(audit.router)



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


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.environment.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


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
