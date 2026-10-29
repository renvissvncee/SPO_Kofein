import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any
from urllib.parse import parse_qsl

from .config import Settings


class AuthenticationError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool = False


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, UnicodeEncodeError) as error:
        raise AuthenticationError("Malformed token") from error


def validate_telegram_init_data(
    init_data: str,
    settings: Settings,
    now: datetime | None = None,
) -> TelegramUser:
    settings.validate_auth()
    if not init_data or len(init_data) > 10_000:
        raise AuthenticationError("Invalid Telegram authentication data")

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as error:
        raise AuthenticationError("Malformed Telegram authentication data") from error
    if len({key for key, _ in pairs}) != len(pairs):
        raise AuthenticationError("Duplicate Telegram authentication fields")

    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise AuthenticationError("Telegram authentication hash is missing")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(data.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        settings.telegram_bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise AuthenticationError("Invalid Telegram authentication signature")

    try:
        auth_date = int(data["auth_date"])
    except (KeyError, TypeError, ValueError) as error:
        raise AuthenticationError("Invalid Telegram authentication date") from error

    current_time = now or datetime.now(timezone.utc)
    age_seconds = int(current_time.timestamp()) - auth_date
    if age_seconds < -30 or age_seconds > settings.telegram_auth_max_age_seconds:
        raise AuthenticationError("Telegram authentication data has expired")

    try:
        user_data = json.loads(data["user"])
        user_id = int(user_data["id"])
        first_name = str(user_data["first_name"]).strip()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise AuthenticationError("Invalid Telegram user data") from error
    if user_id <= 0 or not first_name:
        raise AuthenticationError("Invalid Telegram user data")

    return TelegramUser(
        id=user_id,
        first_name=first_name,
        last_name=_optional_string(user_data.get("last_name")),
        username=_optional_string(user_data.get("username")),
        language_code=_optional_string(user_data.get("language_code")),
        is_premium=bool(user_data.get("is_premium", False)),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def create_access_token(
    telegram_id: int,
    settings: Settings,
    now: datetime | None = None,
) -> tuple[str, int]:
    settings.validate_auth()
    current_time = now or datetime.now(timezone.utc)
    issued_at = int(current_time.timestamp())
    expires_at = issued_at + settings.jwt_ttl_seconds
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(telegram_id),
        "iat": issued_at,
        "exp": expires_at,
        "iss": "kofein-api",
        "aud": "kofein-mini-app",
    }
    encoded_header = _base64url_encode(_json_bytes(header))
    encoded_payload = _base64url_encode(_json_bytes(payload))
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url_encode(signature)}", expires_at


def decode_access_token(
    token: str,
    settings: Settings,
    now: datetime | None = None,
) -> int:
    settings.validate_auth()
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(_base64url_decode(encoded_header))
        payload = json.loads(_base64url_decode(encoded_payload))
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise AuthenticationError("Malformed token") from error

    if header != {"alg": "HS256", "typ": "JWT"}:
        raise AuthenticationError("Unsupported token")

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    received_signature = _base64url_decode(encoded_signature)
    if not hmac.compare_digest(expected_signature, received_signature):
        raise AuthenticationError("Invalid token signature")

    current_timestamp = int((now or datetime.now(timezone.utc)).timestamp())
    try:
        subject = int(payload["sub"])
        issued_at = int(payload["iat"])
        expires_at = int(payload["exp"])
    except (KeyError, TypeError, ValueError) as error:
        raise AuthenticationError("Invalid token claims") from error

    if payload.get("iss") != "kofein-api" or payload.get("aud") != "kofein-mini-app":
        raise AuthenticationError("Invalid token claims")
    if subject <= 0 or issued_at > current_timestamp + 30:
        raise AuthenticationError("Invalid token claims")
    if expires_at <= current_timestamp:
        raise AuthenticationError("Token has expired")
    return subject


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
