import asyncio
import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:test-bot-token")
os.environ.setdefault("MINI_APP_URL", "https://example.com/mini-app/")
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/kofein_test",
)
os.environ["DATABASE_NULL_POOL"] = "true"
os.environ["DEV_AUTH_ENABLED"] = "true"
os.environ["REDIS_URL"] = ""

from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.db.models import engine
from backend.main import app
from backend.services.order_time import get_order_time_store

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "database" / "schema.sql"


async def _reset_database() -> None:
    """Пересоздаёт схему public из database/schema.sql.

    Тесты работают с тем же SQL, что и реальная БД, поэтому заодно проверяют
    сам скрипт схемы.
    """
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        raw = await connection.get_raw_connection()
        await raw.driver_connection.execute(SCHEMA_SQL.read_text(encoding="utf-8"))


def _database_available() -> bool:
    async def ping() -> None:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    try:
        asyncio.run(ping())
    except Exception:
        return False
    return True


_db_checked: bool | None = None


@pytest.fixture
def db() -> None:
    """Чистая БД для интеграционного теста. Без PostgreSQL тест пропускается."""
    global _db_checked
    if _db_checked is None:
        _db_checked = _database_available()
    if not _db_checked:
        pytest.skip("PostgreSQL недоступен (DATABASE_URL), интеграционный тест пропущен")
    asyncio.run(_reset_database())


@pytest.fixture
def client(db) -> Iterator[TestClient]:
    get_order_time_store.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_order_time_store.cache_clear()


@pytest.fixture
def login(client: TestClient) -> Callable[..., dict[str, str]]:
    """Входит через демонстрационный вход и возвращает заголовок Authorization."""

    def _login(telegram_id: int = 100001, first_name: str = "Тест") -> dict[str, str]:
        response = client.post(
            "/api/v1/auth/dev",
            json={"telegram_id": telegram_id, "first_name": first_name},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login
