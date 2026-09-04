"""Crash-recovery endpoint kept separate from the normal episode pipeline."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.episode import Episode
from app.models.user import User
from app.schemas.autosave import AutoSaveOut
from app.services.autosave_service import latest_snapshot

router = APIRouter(prefix="/api/v1/recovery", tags=["recovery"])


@router.get("/{episode_id}", response_model=AutoSaveOut)
def recover_latest(
    episode_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.query(Episode.id).filter(Episode.id == episode_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found.")
    snapshot = latest_snapshot(db, episode_id, user.id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recovery snapshot available.")
    return snapshot
