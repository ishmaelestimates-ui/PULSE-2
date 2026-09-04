"""Authenticated endpoints for isolated editor draft snapshots."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.episode import Episode
from app.models.user import User
from app.schemas.autosave import AutoSaveCreate, AutoSaveOut, AutoSaveStatusOut
from app.services import autosave_service

router = APIRouter(prefix="/api/v1/autosave", tags=["autosave"])


def _require_episode(db: Session, episode_id: int) -> None:
    if db.query(Episode.id).filter(Episode.id == episode_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found.")


@router.post("", response_model=AutoSaveOut, status_code=status.HTTP_201_CREATED)
def create_autosave(
    payload: AutoSaveCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_episode(db, payload.episode_id)
    return autosave_service.save_snapshot(db, payload.episode_id, user.id, payload.data)


@router.get("/{episode_id}", response_model=AutoSaveStatusOut)
def get_latest_autosave(
    episode_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_episode(db, episode_id)
    snapshot = autosave_service.latest_snapshot(db, episode_id, user.id)
    return AutoSaveStatusOut(available=snapshot is not None, snapshot=snapshot)


@router.get("/{episode_id}/history", response_model=list[AutoSaveOut])
def get_autosave_history(
    episode_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_episode(db, episode_id)
    return autosave_service.list_snapshots(db, episode_id, user.id, limit)
