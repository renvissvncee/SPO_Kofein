from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str
    telegram_bot_token: str
    mini_app_url: str
    jwt_secret: str
    jwt_ttl_seconds: int
    telegram_auth_max_age_seconds: int
    cors_origins: tuple[str, ...]

    def validate_auth(self) -> None:
        if not self.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        if len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must contain at least 32 characters")

    def validate_bot(self) -> None:
        self.validate_auth()
        parsed_url = urlparse(self.mini_app_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise RuntimeError("MINI_APP_URL must be a public HTTPS URL")


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


@lru_cache
def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres@localhost:5432/caffein",
        ),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        mini_app_url=os.getenv("MINI_APP_URL", ""),
        jwt_secret=os.getenv("JWT_SECRET", ""),
        jwt_ttl_seconds=_positive_int("JWT_TTL_SECONDS", 3600),
        telegram_auth_max_age_seconds=_positive_int(
            "TELEGRAM_AUTH_MAX_AGE_SECONDS", 3600
        ),
        cors_origins=origins,
    )
