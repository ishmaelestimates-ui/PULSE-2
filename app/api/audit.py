"""Admin read access to the dedicated security audit log."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/api/v1/admin/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None, min_length=1, max_length=120),
    user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    return query.limit(limit).all()
