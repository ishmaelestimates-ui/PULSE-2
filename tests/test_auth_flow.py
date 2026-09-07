import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import auth
from app.api.deps import get_db
from app.config import get_settings
from app.database import Base
from app.models.user import User, UserRole
from app.services.auth_service import hash_password


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'auth.db'}",
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
            password_hash=hash_password("correct-horse-battery-staple"),
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
    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as test_client:
        yield test_client


def test_password_invite_and_magic_link_flow(client):
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct-horse-battery-staple"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    invite = client.post(
        "/api/v1/auth/invites",
        headers=admin_headers,
        json={"email": "editor@example.com", "role": "editor"},
    )
    assert invite.status_code == 201
    invite_token = invite.json()["magic_link_url"].split("token=", 1)[1]

    accepted = client.post(
        "/api/v1/auth/accept-invite",
        json={"token": invite_token, "name": "Editor", "password": "editor-password"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["user"]["email"] == "editor@example.com"

    password_login = client.post(
        "/api/v1/auth/login",
        json={"email": "editor@example.com", "password": "editor-password"},
    )
    assert password_login.status_code == 200
    editor_token = password_login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {editor_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "editor@example.com"

    magic_request = client.post(
        "/api/v1/auth/magic-link/request",
        json={"email": "editor@example.com"},
    )
    assert magic_request.status_code == 200
    magic_token = magic_request.json()["dev_link"].split("token=", 1)[1]

    magic_login = client.post(
        "/api/v1/auth/magic-link/verify",
        json={"token": magic_token},
    )
    assert magic_login.status_code == 200
    assert magic_login.json()["user"]["email"] == "editor@example.com"

    reused_magic_link = client.post(
        "/api/v1/auth/magic-link/verify",
        json={"token": magic_token},
    )
    assert reused_magic_link.status_code == 400


def test_malformed_signed_session_token_is_unauthorized(client):
    token = jwt.encode(
        {"sub": "not-an-integer", "role": "admin"},
        get_settings().secret_key,
        algorithm="HS256",
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired session token."