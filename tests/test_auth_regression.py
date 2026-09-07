from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import auth, episodes, media
from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.database import Base
from app.models.media_file import MediaFile
from app.models.user import User, UserRole
from app.services.auth_service import hash_password
from app.services import media_service


PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def auth_app(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_PATH", str(tmp_path / "media"))
    get_settings.cache_clear()

    engine = create_engine(
        f"sqlite:///{tmp_path / 'auth-regression.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(
        User(
            email="admin@example.com",
            name="Admin",
            role=UserRole.ADMIN,
            password_hash=hash_password(PASSWORD),
        )
    )
    db.commit()
    db.close()

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    test_app = FastAPI()
    test_app.include_router(auth.router)
    private_dependencies = [Depends(get_current_user)]
    test_app.include_router(episodes.router, dependencies=private_dependencies)
    test_app.include_router(media.router, dependencies=private_dependencies)
    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as test_client:
        yield test_client, Session, tmp_path / "media"

    get_settings.cache_clear()


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    return body["access_token"]


def test_valid_login_repeated_login_logout_and_protected_endpoint(auth_app):
    client, _, _ = auth_app

    assert client.get("/api/v1/auth/me").status_code == 401

    for _ in range(3):
        token = login(client)
        headers = {"Authorization": f"Bearer {token}"}
        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "admin@example.com"
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200


def test_invalid_password_and_unknown_user_return_401_without_token(auth_app):
    client, _, _ = auth_app

    for email, password in [
        ("admin@example.com", "wrong-password"),
        ("missing@example.com", PASSWORD),
    ]:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 401
        assert "access_token" not in response.json()


def test_authenticated_media_upload_persists_file_and_record(auth_app, monkeypatch):
    client, Session, media_root = auth_app
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    episode = client.post(
        "/api/v1/episodes",
        headers=headers,
        json={"title": "Auth upload regression"},
    )
    assert episode.status_code == 201
    episode_id = episode.json()["id"]

    monkeypatch.setattr(
        media_service,
        "probe_metadata",
        lambda path: {"duration": 1.0, "codec": "test"},
    )
    monkeypatch.setattr(media_service, "extract_audio", lambda path, _: path)
    monkeypatch.setattr(media_service, "generate_waveform", lambda _: [0.0])
    monkeypatch.setattr(media_service, "classify_media_type", media_service.classify_media_type)

    upload = client.post(
        f"/api/v1/episodes/{episode_id}/media",
        headers=headers,
        files={"file": ("fixture.wav", b"PULSE-test-media", "audio/wav")},
    )
    assert upload.status_code == 201
    media_body = upload.json()["media_file"]
    assert media_body["filename"] == "fixture.wav"
    assert media_body["file_size"] == len(b"PULSE-test-media")
    assert media_body["url"] == f"/media/uploads/{episode_id}/" + next(
        path.name for path in (media_root / "uploads" / str(episode_id)).iterdir()
    )

    with Session() as db:
        record = db.query(MediaFile).filter(MediaFile.id == media_body["id"]).one()
        assert record.episode_id == episode_id
        assert Path(record.file_path).exists()


def test_production_rejects_unconfigured_cors_default():
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(
            environment="production",
            database_url="postgresql://configured/database",
            secret_key="a" * 32,
            bootstrap_admin_password="a" * 12,
        )