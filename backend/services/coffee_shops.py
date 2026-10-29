from datetime import time
from uuid import UUID

from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import CoffeeShop, CoffeeShopOwner, Order, User
from ..errors import ConflictError, NotFoundError
from ..schemas import CoffeeShopCreate, CoffeeShopUpdate


def is_open_at(shop: CoffeeShop, moment: time) -> bool:
    """Открыта ли кофейня в момент moment. Учитывает работу через полночь."""
    if shop.opening_time < shop.closing_time:
        return shop.opening_time <= moment < shop.closing_time
    return moment >= shop.opening_time or moment < shop.closing_time


async def list_public(
    session: AsyncSession,
    query: str | None = None,
    district: str | None = None,
    open_at: time | None = None,
) -> list[CoffeeShop]:
    statement = select(CoffeeShop).where(CoffeeShop.is_active.is_(True))
    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                CoffeeShop.name.ilike(pattern),
                CoffeeShop.address.ilike(pattern),
                CoffeeShop.district.ilike(pattern),
            )
        )
    if district:
        statement = statement.where(func.lower(CoffeeShop.district) == district.strip().lower())
    shops = list((await session.scalars(statement.order_by(CoffeeShop.name))).all())
    if open_at is not None:
        shops = [shop for shop in shops if is_open_at(shop, open_at)]
    return shops


async def get_active(session: AsyncSession, shop_id: UUID) -> CoffeeShop:
    shop = await session.get(CoffeeShop, shop_id)
    if shop is None or not shop.is_active:
        raise NotFoundError("Кофейня не найдена")
    return shop


async def get_any(session: AsyncSession, shop_id: UUID) -> CoffeeShop:
    shop = await session.get(CoffeeShop, shop_id)
    if shop is None:
        raise NotFoundError("Кофейня не найдена")
    return shop


async def list_owned(session: AsyncSession, telegram_id: int) -> list[CoffeeShop]:
    statement = (
        select(CoffeeShop)
        .join(CoffeeShopOwner)
        .where(CoffeeShopOwner.telegram_id == telegram_id)
        .order_by(CoffeeShop.name)
    )
    return list((await session.scalars(statement)).all())


async def create(session: AsyncSession, owner_id: int, data: CoffeeShopCreate) -> CoffeeShop:
    """Создаёт кофейню; создатель становится её первым владельцем."""
    shop = CoffeeShop(**data.model_dump())
    shop.ownerships.append(CoffeeShopOwner(telegram_id=owner_id))
    session.add(shop)
    await session.commit()
    await session.refresh(shop)
    return shop


async def update(session: AsyncSession, shop_id: UUID, data: CoffeeShopUpdate) -> CoffeeShop:
    shop = await get_any(session, shop_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(shop, field, value)
    if shop.opening_time == shop.closing_time:
        raise ConflictError("Время открытия и закрытия не может совпадать")
    await session.commit()
    await session.refresh(shop)
    return shop


async def remove(session: AsyncSession, shop_id: UUID) -> None:
    """Удаляет кофейню вместе с меню, избранным и корзинами.

    Если по кофейне есть оформленные заказы, удаление запрещено: история
    заказов покупателей должна сохраниться. Такую кофейню можно скрыть через
    is_active = false.
    """
    shop = await get_any(session, shop_id)
    has_orders = await session.scalar(
        select(exists().where(Order.coffee_shop_id == shop_id, Order.status != "cart"))
    )
    if has_orders:
        raise ConflictError(
            "У кофейни есть оформленные заказы. Скройте её через is_active = false",
            code="SHOP_HAS_ORDERS",
        )
    await session.execute(delete(Order).where(Order.coffee_shop_id == shop_id))
    await session.delete(shop)
    await session.commit()


# ---------- Владельцы ----------


async def list_owners(session: AsyncSession, shop_id: UUID) -> list[User]:
    statement = (
        select(User)
        .join(CoffeeShopOwner)
        .where(CoffeeShopOwner.coffee_shop_id == shop_id)
        .order_by(User.telegram_id)
    )
    return list((await session.scalars(statement)).all())


async def add_owner(session: AsyncSession, shop_id: UUID, telegram_id: int) -> User:
    user = await session.get(User, telegram_id)
    if user is None:
        raise NotFoundError("Пользователь не найден: он должен хотя бы раз войти в Mini App")
    link = await session.get(CoffeeShopOwner, (shop_id, telegram_id))
    if link is None:
        session.add(CoffeeShopOwner(coffee_shop_id=shop_id, telegram_id=telegram_id))
        await session.commit()
    return user


async def remove_owner(session: AsyncSession, shop_id: UUID, telegram_id: int) -> None:
    link = await session.get(CoffeeShopOwner, (shop_id, telegram_id))
    if link is None:
        raise NotFoundError("Пользователь не является владельцем этой кофейни")
    owners_count = await session.scalar(
        select(func.count())
        .select_from(CoffeeShopOwner)
        .where(CoffeeShopOwner.coffee_shop_id == shop_id)
    )
    if owners_count == 1:
        raise ConflictError("Нельзя удалить последнего владельца кофейни", code="LAST_OWNER")
    await session.delete(link)
    await session.commit()
