"""
Brand settings endpoints.

Single global settings row (see app/models/brand_settings.py for why —
there's no auth/user system yet). Logo and intro/outro music are stored
as plain uploaded files under MEDIA_STORAGE_PATH/brand/, reusing the same
static-serving mount as episode media.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.brand_settings import BrandSettings
from app.schemas.color import BrandSettingsOut, BrandSettingsUpdate
from app.services import media_service

router = APIRouter(prefix="/api/v1/brand-settings", tags=["brand-settings"])

_SINGLETON_ID = 1

_ALLOWED_LOGO_EXT = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
_ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".flac", ".aac"}


def _get_or_create(db: Session) -> BrandSettings:
    settings_row = db.query(BrandSettings).filter(BrandSettings.id == _SINGLETON_ID).first()
    if settings_row is None:
        settings_row = BrandSettings(id=_SINGLETON_ID)
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


def _brand_dir() -> Path:
    settings = get_settings()
    directory = Path(settings.media_storage_path) / "brand"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _to_out(row: BrandSettings) -> BrandSettingsOut:
    out = BrandSettingsOut.model_validate(row)
    if row.logo_path:
        out.logo_url = media_service.build_media_url(Path(row.logo_path))
    if row.intro_music_path:
        out.intro_music_url = media_service.build_media_url(Path(row.intro_music_path))
    if row.outro_music_path:
        out.outro_music_url = media_service.build_media_url(Path(row.outro_music_path))
    return out


@router.get("", response_model=BrandSettingsOut)
def get_brand_settings(db: Session = Depends(get_db)):
    return _to_out(_get_or_create(db))


@router.put("", response_model=BrandSettingsOut)
def update_brand_settings(payload: BrandSettingsUpdate, db: Session = Depends(get_db)):
    row = _get_or_create(db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(row, field, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


async def _save_named_upload(
    db: Session, file: UploadFile, allowed_ext: set[str], target_field: str, prefix: str
) -> BrandSettings:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed_ext))}",
        )
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")

    dest = _brand_dir() / f"{prefix}{ext}"
    dest.write_bytes(contents)

    row = _get_or_create(db)
    setattr(row, target_field, str(dest))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/logo", response_model=BrandSettingsOut)
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    row = await _save_named_upload(db, file, _ALLOWED_LOGO_EXT, "logo_path", "logo")
    return _to_out(row)


@router.post("/intro-music", response_model=BrandSettingsOut)
async def upload_intro_music(file: UploadFile = File(...), db: Session = Depends(get_db)):
    row = await _save_named_upload(db, file, _ALLOWED_AUDIO_EXT, "intro_music_path", "intro_music")
    return _to_out(row)


@router.post("/outro-music", response_model=BrandSettingsOut)
async def upload_outro_music(file: UploadFile = File(...), db: Session = Depends(get_db)):
    row = await _save_named_upload(db, file, _ALLOWED_AUDIO_EXT, "outro_music_path", "outro_music")
    return _to_out(row)
