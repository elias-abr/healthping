"""Tests for authentication endpoints and utilities."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from healthping.api import create_app
from healthping.auth.passwords import hash_password, verify_password
from healthping.auth.tokens import create_access_token, decode_access_token
from healthping.db.base import Base
from healthping.settings import Settings
from healthping.state import MonitorState


@pytest.fixture()
def settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        jwt_secret="test-secret-key-for-tests-only",
        db_path=":memory:",
    )


@pytest.fixture()
async def session_factory(settings: Settings):  # type: ignore[no-untyped-def]
    url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture()
def client(session_factory: object, settings: Settings) -> TestClient:
    app = create_app(
        state=MonitorState(),
        allowed_origins=["*"],
        session_factory=session_factory,  # type: ignore[arg-type]
        settings=settings,
    )
    return TestClient(app, raise_server_exceptions=True)


# ── password utilities ────────────────────────────────────────────────────────


def test_password_hashing_roundtrip() -> None:
    hashed = hash_password("correct-horse-battery")
    assert verify_password("correct-horse-battery", hashed)
    assert not verify_password("wrong-password", hashed)


# ── token utilities ───────────────────────────────────────────────────────────


def test_token_roundtrip(settings: Settings) -> None:
    token = create_access_token(
        user_id=42,
        email="test@example.com",
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expiry_days=settings.jwt_expiry_days,
    )
    payload = decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "test@example.com"


def test_decode_invalid_token(settings: Settings) -> None:
    result = decode_access_token("not-a-token", settings.jwt_secret, settings.jwt_algorithm)
    assert result is None


# ── signup ────────────────────────────────────────────────────────────────────


def test_signup_creates_user(client: TestClient) -> None:
    r = client.post("/api/auth/signup", json={"email": "user@example.com", "password": "password123"})
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "user@example.com"
    assert "id" in data
    assert "password" not in data


def test_signup_rejects_duplicate_email(client: TestClient) -> None:
    client.post("/api/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    r = client.post("/api/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    assert r.status_code == 409


def test_signup_rejects_short_password(client: TestClient) -> None:
    r = client.post("/api/auth/signup", json={"email": "user@example.com", "password": "short"})
    assert r.status_code == 422


def test_signup_rejects_invalid_email(client: TestClient) -> None:
    r = client.post("/api/auth/signup", json={"email": "not-an-email", "password": "password123"})
    assert r.status_code == 422


# ── login ─────────────────────────────────────────────────────────────────────


def test_login_returns_token_on_valid_credentials(client: TestClient) -> None:
    client.post("/api/auth/signup", json={"email": "login@example.com", "password": "password123"})
    r = client.post("/api/auth/login", json={"email": "login@example.com", "password": "password123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post("/api/auth/signup", json={"email": "wrong@example.com", "password": "password123"})
    r = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "wrongpassword"})
    assert r.status_code == 401


def test_login_rejects_nonexistent_email(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "password123"})
    assert r.status_code == 401


# ── me ────────────────────────────────────────────────────────────────────────


def test_me_returns_current_user_when_authenticated(client: TestClient) -> None:
    client.post("/api/auth/signup", json={"email": "me@example.com", "password": "password123"})
    login_r = client.post("/api/auth/login", json={"email": "me@example.com", "password": "password123"})
    token = login_r.json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


def test_me_returns_401_when_not_authenticated(client: TestClient) -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 401


# ── logout ────────────────────────────────────────────────────────────────────


def test_logout_clears_session(client: TestClient) -> None:
    client.post("/api/auth/signup", json={"email": "logout@example.com", "password": "password123"})
    client.post("/api/auth/login", json={"email": "logout@example.com", "password": "password123"})
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    # Cookie should be cleared
    assert "healthping_session" not in client.cookies
