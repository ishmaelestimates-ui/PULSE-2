"""Unit tests for the isolated autosave service."""
import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa: F401 - register all parent tables
from app.models.autosave import AutoSave
from app.services.autosave_service import latest_snapshot, save_snapshot, list_snapshots


def test_autosave_round_trip_and_latest():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        # Use explicit IDs only for the isolated test table's foreign keys.
        db.execute(__import__('sqlalchemy').text("INSERT INTO users (id, email, role, is_active, created_at) VALUES (1, 'test@example.com', 'editor', 1, :now)"), {"now": datetime.now(timezone.utc)})
        db.execute(__import__('sqlalchemy').text("INSERT INTO episodes (id, title, created_at) VALUES (1, 'Test', :now)"), {"now": datetime.now(timezone.utc)})
        db.commit()
        first = save_snapshot(db, 1, 1, {"title": "draft 1"})
        second = save_snapshot(db, 1, 1, {"title": "draft 2"})
        assert first.id != second.id
        assert latest_snapshot(db, 1, 1).data == {"title": "draft 2"}
        assert len(list_snapshots(db, 1, 1)) == 2
    finally:
        db.close()
