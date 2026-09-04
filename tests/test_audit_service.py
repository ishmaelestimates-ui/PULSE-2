import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base, SessionLocal, engine
from app.models import User
from app.models.audit_log import AuditLog
from app.services.audit_service import record_event, sanitize_metadata


def test_audit_metadata_filters_secrets():
    clean = sanitize_metadata({
        "episode_id": 7,
        "Authorization": "Bearer secret",
        "nested": {"password": "hidden", "ok": "yes"},
    })
    assert clean == {"episode_id": 7, "nested": {"ok": "yes"}}


def test_record_event_persists_safe_event():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        user = User(email="audit@example.com", name="Audit Tester")
        db.add(user)
        db.commit()
        db.refresh(user)

        event = record_event(
            db,
            action="episode_exported",
            user_id=user.id,
            method="POST",
            route="/api/v1/episodes/7/export",
            status_code=200,
            resource_type="episode",
            resource_id=7,
            metadata={"format": "resolve_csv", "token": "must-not-store"},
        )

        stored = db.query(AuditLog).filter(AuditLog.id == event.id).one()
        assert stored.user_id == user.id
        assert stored.action == "episode_exported"
        assert stored.metadata_json == {"format": "resolve_csv"}
    finally:
        db.close()
        Base.metadata.drop_all(engine)
