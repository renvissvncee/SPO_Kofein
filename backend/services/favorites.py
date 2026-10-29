from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import CoffeeShop, Favorite
from ..errors import NotFoundError
from . import coffee_shops


async def list_shops(session: AsyncSession, telegram_id: int) -> list[CoffeeShop]:
    statement = (
        select(CoffeeShop)
        .join(Favorite)
        .where(Favorite.telegram_id == telegram_id)
        .order_by(Favorite.created_at)
    )
    return list((await session.scalars(statement)).all())


async def add(session: AsyncSession, telegram_id: int, shop_id: UUID) -> bool:
    """Добавляет кофейню в избранное. Возвращает True, если запись создана."""
    await coffee_shops.get_active(session, shop_id)
    existing = await session.scalar(
        select(Favorite).where(
            Favorite.telegram_id == telegram_id, Favorite.coffee_shop_id == shop_id
        )
    )
    if existing is not None:
        return False
    session.add(Favorite(telegram_id=telegram_id, coffee_shop_id=shop_id))
    await session.commit()
    return True


async def remove(session: AsyncSession, telegram_id: int, shop_id: UUID) -> None:
    favorite = await session.scalar(
        select(Favorite).where(
            Favorite.telegram_id == telegram_id, Favorite.coffee_shop_id == shop_id
        )
    )
    if favorite is None:
        raise NotFoundError("Кофейни нет в избранном")
    await session.delete(favorite)
    await session.commit()
