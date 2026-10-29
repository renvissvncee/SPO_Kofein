from datetime import UTC, datetime, timedelta

import pytest

from backend.config import Settings
from backend.security import (
    AuthenticationError,
    create_access_token,
    decode_access_token,
    validate_telegram_init_data,
)
from backend.tests.helpers import make_init_data

BOT_TOKEN = "123456789:test-bot-token"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://postgres@localhost/test",
        telegram_bot_token=BOT_TOKEN,
        mini_app_url="https://example.com/mini-app/",
        jwt_secret="a-secure-test-secret-with-more-than-32-characters",
        jwt_ttl_seconds=3600,
        telegram_auth_max_age_seconds=3600,
        cors_origins=("http://localhost:5173",),
    )


def test_valid_telegram_init_data_is_accepted(settings: Settings) -> None:
    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    init_data = make_init_data(BOT_TOKEN, auth_date=int(now.timestamp()))

    user = validate_telegram_init_data(init_data, settings, now=now)

    assert user.id == 100001
    assert user.username == "artem_test"
    assert user.is_premium is True


def test_tampered_telegram_init_data_is_rejected(settings: Settings) -> None:
    init_data = make_init_data(BOT_TOKEN)
    init_data = init_data.replace("Artem", "Mallory")

    with pytest.raises(AuthenticationError, match="signature"):
        validate_telegram_init_data(init_data, settings)


def test_expired_telegram_init_data_is_rejected(settings: Settings) -> None:
    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    old_date = int((now - timedelta(hours=2)).timestamp())

    with pytest.raises(AuthenticationError, match="expired"):
        validate_telegram_init_data(
            make_init_data(BOT_TOKEN, auth_date=old_date),
            settings,
            now=now,
        )


def test_access_token_round_trip(settings: Settings) -> None:
    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    token, expires_at = create_access_token(100001, settings, now=now)

    assert decode_access_token(token, settings, now=now) == 100001
    assert expires_at == int(now.timestamp()) + 3600


def test_tampered_access_token_is_rejected(settings: Settings) -> None:
    token, _ = create_access_token(100001, settings)
    head, payload, signature = token.split(".")
    # Меняем первый символ: последний символ base64url несёт лишь часть битов,
    # и его замена иногда не меняет подпись (тест падал примерно в 1 из 16 запусков).
    replacement = "B" if signature[0] == "A" else "A"
    tampered_token = f"{head}.{payload}.{replacement}{signature[1:]}"

    with pytest.raises(AuthenticationError, match="signature"):
        decode_access_token(tampered_token, settings)


def test_expired_access_token_is_rejected(settings: Settings) -> None:
    issued_at = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    token, _ = create_access_token(100001, settings, now=issued_at)

    with pytest.raises(AuthenticationError, match="expired"):
        decode_access_token(
            token,
            settings,
            now=issued_at + timedelta(hours=2),
        )
