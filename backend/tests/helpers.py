from datetime import datetime, timezone
import hashlib
import hmac
import json
from urllib.parse import urlencode


def make_init_data(
    bot_token: str,
    telegram_id: int = 100001,
    auth_date: int | None = None,
) -> str:
    if auth_date is None:
        auth_date = int(datetime.now(timezone.utc).timestamp())
    data = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {
                "id": telegram_id,
                "first_name": "Artem",
                "last_name": "Testov",
                "username": "artem_test",
                "language_code": "ru",
                "is_premium": True,
            },
            separators=(",", ":"),
        ),
    }
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(
        secret_key, check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(data)
