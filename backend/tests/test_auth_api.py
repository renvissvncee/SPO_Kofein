"""Аутентификация на уровне API. Эти тесты не требуют PostgreSQL."""

import dataclasses
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import backend.auth as auth_module
import backend.main as main_module
from backend.config import get_settings
from backend.security import create_access_token
from backend.tests.helpers import make_init_data

PROTECTED_ENDPOINTS = [
    ("GET", "/api/v1/me"),
    ("GET", "/api/v1/me/favorites"),
    ("GET", "/api/v1/me/carts"),
    ("POST", "/api/v1/me/orders"),
    ("GET", "/api/v1/me/coffee-shops"),
    ("POST", "/api/v1/coffee-shops"),
    ("PATCH", "/api/v1/coffee-shops/11111111-1111-1111-1111-111111111111"),
    ("GET", "/api/v1/coffee-shops/11111111-1111-1111-1111-111111111111/orders"),
]


def bearer_token(telegram_id: int = 100001) -> str:
    token, _ = create_access_token(telegram_id, get_settings())
    return token


@pytest.fixture
def api() -> TestClient:
    with TestClient(main_module.app) as client:
        yield client


def test_telegram_auth_registers_user_and_returns_jwt(monkeypatch, api) -> None:
    async def fake_upsert(telegram_user, session):
        return SimpleNamespace(
            telegram_id=telegram_user.id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            language_code=telegram_user.language_code,
            is_premium=telegram_user.is_premium,
            phone=None,
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(auth_module, "upsert_telegram_user", fake_upsert)
    response = api.post(
        "/api/v1/auth/telegram",
        json={"init_data": make_init_data(get_settings().telegram_bot_token)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["telegram_id"] == 100001
    assert body["access_token"].count(".") == 2


def test_invalid_telegram_signature_returns_401(api) -> None:
    init_data = make_init_data(get_settings().telegram_bot_token).replace("Artem", "Mallory")
    response = api.post("/api/v1/auth/telegram", json={"init_data": init_data})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_empty_init_data_returns_422_in_common_format(api) -> None:
    response = api.post("/api/v1/auth/telegram", json={"init_data": ""})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"] == "body.init_data"


@pytest.mark.parametrize(("method", "path"), PROTECTED_ENDPOINTS)
def test_protected_endpoint_rejects_missing_jwt(api, method, path) -> None:
    response = api.request(method, path, json={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize(("method", "path"), PROTECTED_ENDPOINTS)
def test_protected_endpoint_rejects_invalid_jwt(api, method, path) -> None:
    response = api.request(method, path, json={}, headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401


def test_jwt_signed_with_other_secret_is_rejected(api) -> None:
    foreign = dataclasses.replace(get_settings(), jwt_secret="x" * 40)
    token, _ = create_access_token(100001, foreign)
    response = api.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert "signature" in response.json()["error"]["message"]


def test_non_bearer_scheme_is_rejected(api) -> None:
    response = api.get("/api/v1/me", headers={"Authorization": f"Basic {bearer_token()}"})

    assert response.status_code == 401


def test_dev_login_is_hidden_when_disabled(monkeypatch, api) -> None:
    disabled = dataclasses.replace(get_settings(), dev_auth_enabled=False)
    monkeypatch.setattr(auth_module, "get_settings", lambda: disabled)
    response = api.post("/api/v1/auth/dev", json={"telegram_id": 1})

    assert response.status_code == 404


def test_health_endpoint_is_public(api) -> None:
    response = api.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mini_app_frontend_is_served(api) -> None:
    response = api.get("/mini-app/")

    assert response.status_code == 200
    assert "telegram-web-app.js" in response.text
    assert "/mini-app/app.js" in response.text


def test_unknown_route_uses_common_error_format(api) -> None:
    response = api.get("/api/v1/unknown")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
