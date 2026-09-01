"""
User management endpoints (admin only, except a user viewing their own
activity).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.user import ActivityLogEntry, User
from app.schemas.user import UserActivityResponse, UserOut, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.created_at).all()


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if user_id == admin.id and payload.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't deactivate your own account.")

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("/{user_id}/activity", response_model=UserActivityResponse)
def get_user_activity(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    if current.role != "admin" and current.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own activity.")

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    activity = (
        db.query(ActivityLogEntry)
        .filter(ActivityLogEntry.user_id == user_id)
        .order_by(ActivityLogEntry.created_at.desc())
        .all()
    )
    return UserActivityResponse(user=target, activity=activity)
