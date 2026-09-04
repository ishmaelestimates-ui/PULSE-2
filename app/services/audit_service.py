"""Small, explicit audit-event persistence service.

Callers provide safe, already-sanitized metadata. This service deliberately
rejects common credential fields so a future caller cannot accidentally persist
secrets in the audit table.
"""
from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

_FORBIDDEN_KEYS = {
    "authorization",
    "cookie",
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "invite_token",
    "magic_link_token",
    "secret",
    "api_key",
}


def sanitize_metadata(metadata: Mapping | None) -> dict | None:
    if metadata is None:
        return None
    clean: dict = {}
    for key, value in metadata.items():
        normalized = str(key).strip().lower()
        if normalized in _FORBIDDEN_KEYS:
            continue
        if isinstance(value, Mapping):
            clean[str(key)] = sanitize_metadata(value) or {}
        elif isinstance(value, (str, int, float, bool)) or value is None:
            clean[str(key)] = value
        else:
            clean[str(key)] = str(value)
    return clean


def record_event(
    db: Session,
    *,
    action: str,
    user_id: int | None = None,
    method: str | None = None,
    route: str | None = None,
    status_code: int | None = None,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    metadata: Mapping | None = None,
) -> AuditLog:
    event = AuditLog(
        user_id=user_id,
        action=action[:120],
        method=method[:10] if method else None,
        route=route[:255] if route else None,
        status_code=status_code,
        resource_type=resource_type[:80] if resource_type else None,
        resource_id=str(resource_id)[:120] if resource_id is not None else None,
        metadata_json=sanitize_metadata(metadata),
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
