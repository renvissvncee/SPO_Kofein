from redis.asyncio import Redis, ConnectionPool
import datetime
import json
from typing import Optional
from .crud import get_all_coffee_shops

pool = ConnectionPool.from_url(url='redis://localhost', max_connections=200, decode_responses=True)
redis = Redis(connection_pool=pool)


async def crud_redis_time_order(tg_id: int, date: Optional[str] = None, action: str = "create"):
    """
    Управляет записью в Redis для Telegram ID.

    :param tg_id: Telegram ID пользователя
    :param date: Дата в строковом формате (обязательна для create и update)
    :param action: Действие - "create", "update" или "delete"
    """
    key = f"tg:{tg_id}"
    if action == "create":
        if date is None:
            raise ValueError(f"date required for create action {date}")
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            "date": date,
            "created_at": now
        }
        await redis.set(key, json.dumps(data))
        shops = await get_all_coffee_shops(order_time=date)
        return shops
    
    elif action == "update":
        if date is None:
            raise ValueError("date required for update action")
        existing = await redis.get(key)
        if existing:
            data = json.loads(existing)
            data["created_at"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data["date"] = date
            await redis.set(key, json.dumps(data))
            shops = await get_all_coffee_shops(order_time=date)
            return shops
        else:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data = {
                "date": date,
                "created_at": now
            }
            shops = await get_all_coffee_shops(order_time=date)
            return shops
    
    elif action == "delete":
        await redis.delete(key)
        return {"message": "Record deleted"}
    elif action == "get":
        existing = await redis.get(key)
        if existing:
            return json.loads(existing)
        return None
    

    else:
        raise ValueError("Invalid action. Use 'create', 'update', 'get', or 'delete'")

