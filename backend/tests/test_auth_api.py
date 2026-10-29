from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import backend.auth as auth_module
import backend.main as main_module
from backend.auth import (
    JWTAuthenticationMiddleware,
    require_coffee_shop_owner,
)
from backend.config import get_settings
from backend.db.models import session_dependency
from backend.security import create_access_token
from backend.tests.helpers import make_init_data


def bearer_token(telegram_id: int = 100001) -> str:
    token, _ = create_access_token(telegram_id, get_settings())
    return token


def test_telegram_auth_registers_user_and_returns_jwt(monkeypatch) -> None:
    async def fake_upsert(telegram_user, session):
        return SimpleNamespace(
            telegram_id=telegram_user.id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            language_code=telegram_user.language_code,
            is_premium=telegram_user.is_premium,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(auth_module, "upsert_telegram_user", fake_upsert)
    with TestClient(main_module.app) as client:
        response = client.post(
            "/auth/telegram",
            json={"init_data": make_init_data(get_settings().telegram_bot_token)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["telegram_id"] == 100001
    assert body["access_token"].count(".") == 2


def test_invalid_telegram_signature_returns_401() -> None:
    init_data = make_init_data(get_settings().telegram_bot_token).replace(
        "Artem", "Mallory"
    )
    with TestClient(main_module.app) as client:
        response = client.post("/auth/telegram", json={"init_data": init_data})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_endpoint_rejects_missing_jwt() -> None:
    with TestClient(main_module.app) as client:
        response = client.get("/favorites")

    assert response.status_code == 401


def test_health_endpoint_is_public() -> None:
    with TestClient(main_module.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mini_app_frontend_is_served() -> None:
    with TestClient(main_module.app) as client:
        response = client.get("/mini-app/")

    assert response.status_code == 200
    assert "telegram-web-app.js" in response.text
    assert "/mini-app/app.js" in response.text


def test_protected_endpoint_rejects_invalid_jwt() -> None:
    with TestClient(main_module.app) as client:
        response = client.get(
            "/favorites", headers={"Authorization": "Bearer invalid-token"}
        )

    assert response.status_code == 401


def test_protected_endpoint_uses_identity_from_jwt(monkeypatch) -> None:
    received_ids: list[int] = []

    async def fake_get_favorites(telegram_id: int):
        received_ids.append(telegram_id)
        return []

    monkeypatch.setattr(main_module, "get_favorites", fake_get_favorites)
    with TestClient(main_module.app) as client:
        response = client.get(
            "/favorites?tg_id=999999",
            headers={"Authorization": f"Bearer {bearer_token(100001)}"},
        )

    assert response.status_code == 200
    assert received_ids == [100001]


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, owner_exists: bool):
        self.owner_exists = owner_exists

    async def execute(self, statement):
        return FakeResult(object() if self.owner_exists else None)


def owner_test_app(owner_exists: bool) -> FastAPI:
    app = FastAPI()
    app.add_middleware(JWTAuthenticationMiddleware)

    async def fake_session():
        yield FakeSession(owner_exists)

    app.dependency_overrides[session_dependency] = fake_session

    @app.patch("/coffee-shops/{coffee_shop_id}")
    async def owner_only_endpoint(
        coffee_shop_id,
        telegram_id: int = Depends(require_coffee_shop_owner),
    ):
        return {"telegram_id": telegram_id}

    return app


def test_non_owner_receives_403() -> None:
    app = owner_test_app(owner_exists=False)
    with TestClient(app) as client:
        response = client.patch(
            f"/coffee-shops/{uuid4()}",
            headers={"Authorization": f"Bearer {bearer_token()}"},
        )

    assert response.status_code == 403


def test_owner_is_allowed() -> None:
    app = owner_test_app(owner_exists=True)
    with TestClient(app) as client:
        response = client.patch(
            f"/coffee-shops/{uuid4()}",
            headers={"Authorization": f"Bearer {bearer_token()}"},
        )

    assert response.status_code == 200
    assert response.json() == {"telegram_id": 100001}
