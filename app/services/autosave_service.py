"""Small, isolated persistence layer for editor draft snapshots."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.autosave import AutoSave

MAX_SNAPSHOTS_PER_USER_EPISODE = 20


def save_snapshot(db: Session, episode_id: int, user_id: int, data: dict) -> AutoSave:
    snapshot = AutoSave(
        episode_id=episode_id,
        user_id=user_id,
        data=data,
        saved_at=datetime.now(timezone.utc),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    _prune_old_snapshots(db, episode_id, user_id)
    return snapshot


def latest_snapshot(db: Session, episode_id: int, user_id: int) -> AutoSave | None:
    return (
        db.query(AutoSave)
        .filter(AutoSave.episode_id == episode_id, AutoSave.user_id == user_id)
        .order_by(AutoSave.saved_at.desc(), AutoSave.id.desc())
        .first()
    )


def list_snapshots(db: Session, episode_id: int, user_id: int, limit: int = 10) -> list[AutoSave]:
    limit = max(1, min(limit, MAX_SNAPSHOTS_PER_USER_EPISODE))
    return (
        db.query(AutoSave)
        .filter(AutoSave.episode_id == episode_id, AutoSave.user_id == user_id)
        .order_by(AutoSave.saved_at.desc(), AutoSave.id.desc())
        .limit(limit)
        .all()
    )


def _prune_old_snapshots(db: Session, episode_id: int, user_id: int) -> None:
    ids = [
        row.id
        for row in (
            db.query(AutoSave.id)
            .filter(AutoSave.episode_id == episode_id, AutoSave.user_id == user_id)
            .order_by(AutoSave.saved_at.desc(), AutoSave.id.desc())
            .offset(MAX_SNAPSHOTS_PER_USER_EPISODE)
            .all()
        )
    ]
    if ids:
        db.query(AutoSave).filter(AutoSave.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
