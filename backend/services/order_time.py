"""Время заказа, выбранное пользователем до оформления.

Хранится в Redis под ключом tg:{telegram_id} (как было в db/cache.py).
Если REDIS_URL не задан, используется хранилище в памяти процесса:
этого достаточно для разработки и тестов.
"""

import json
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol

from ..config import get_settings


class OrderTimeStore(Protocol):
    async def get(self, telegram_id: int) -> dict[str, datetime] | None: ...

    async def set(self, telegram_id: int, order_time: datetime) -> dict[str, datetime]: ...

    async def delete(self, telegram_id: int) -> bool: ...


def _record(order_time: datetime) -> dict[str, datetime]:
    return {"order_time": order_time, "updated_at": datetime.now(UTC)}


class MemoryOrderTimeStore:
    def __init__(self) -> None:
        self._data: dict[int, dict[str, datetime]] = {}

    async def get(self, telegram_id: int) -> dict[str, datetime] | None:
        return self._data.get(telegram_id)

    async def set(self, telegram_id: int, order_time: datetime) -> dict[str, datetime]:
        self._data[telegram_id] = _record(order_time)
        return self._data[telegram_id]

    async def delete(self, telegram_id: int) -> bool:
        return self._data.pop(telegram_id, None) is not None


class RedisOrderTimeStore:
    # Выбранное время теряет смысл через сутки
    ttl_seconds = 24 * 60 * 60

    def __init__(self, url: str) -> None:
        from redis.asyncio import Redis

        self._redis = Redis.from_url(url, decode_responses=True)

    @staticmethod
    def _key(telegram_id: int) -> str:
        return f"tg:{telegram_id}"

    async def get(self, telegram_id: int) -> dict[str, datetime] | None:
        raw = await self._redis.get(self._key(telegram_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return {key: datetime.fromisoformat(value) for key, value in data.items()}

    async def set(self, telegram_id: int, order_time: datetime) -> dict[str, datetime]:
        record = _record(order_time)
        payload = {key: value.isoformat() for key, value in record.items()}
        await self._redis.set(self._key(telegram_id), json.dumps(payload), ex=self.ttl_seconds)
        return record

    async def delete(self, telegram_id: int) -> bool:
        return bool(await self._redis.delete(self._key(telegram_id)))


@lru_cache
def get_order_time_store() -> OrderTimeStore:
    url = get_settings().redis_url
    return RedisOrderTimeStore(url) if url else MemoryOrderTimeStore()
