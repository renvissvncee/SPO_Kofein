import os


os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:test-bot-token")
os.environ.setdefault("MINI_APP_URL", "https://example.com/mini-app/")
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-characters-long")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/caffein_test",
)
