import pytest

from backend.bot import mini_app_url
from backend.config import Settings


def test_mini_app_url_has_trailing_slash() -> None:
    assert mini_app_url() == "https://example.com/mini-app/"


def test_bot_rejects_non_https_mini_app_url() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://postgres@localhost/test",
        telegram_bot_token="123456789:test-bot-token",
        mini_app_url="http://localhost:8000/mini-app/",
        jwt_secret="a-secure-test-secret-with-more-than-32-characters",
        jwt_ttl_seconds=3600,
        telegram_auth_max_age_seconds=3600,
        cors_origins=("http://localhost:5173",),
    )

    with pytest.raises(RuntimeError, match="HTTPS"):
        settings.validate_bot()
