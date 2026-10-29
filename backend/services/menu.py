from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db.models import MenuCategory, MenuItem, Order, OrderItem
from ..errors import ConflictError, NotFoundError
from ..schemas import MenuCategoryCreate, MenuCategoryUpdate, MenuItemCreate, MenuItemUpdate
from . import carts


async def get_menu(session: AsyncSession, shop_id: UUID) -> list[MenuCategory]:
    """Категории кофейни с позициями. Недоступные позиции тоже возвращаются,
    с is_available = false, чтобы клиент мог пометить их «Нет в наличии»."""
    statement = (
        select(MenuCategory)
        .where(MenuCategory.coffee_shop_id == shop_id)
        .options(selectinload(MenuCategory.menu_items))
        .order_by(MenuCategory.name)
    )
    return list((await session.scalars(statement)).all())


# ---------- Категории ----------


async def _get_category(session: AsyncSession, shop_id: UUID, category_id: UUID) -> MenuCategory:
    category = await session.get(MenuCategory, category_id)
    if category is None or category.coffee_shop_id != shop_id:
        raise NotFoundError("Категория не найдена")
    return category


async def _ensure_unique_category_name(
    session: AsyncSession, shop_id: UUID, name: str, exclude_id: UUID | None = None
) -> None:
    statement = select(MenuCategory.id).where(
        MenuCategory.coffee_shop_id == shop_id, MenuCategory.name == name
    )
    if exclude_id is not None:
        statement = statement.where(MenuCategory.id != exclude_id)
    if await session.scalar(statement) is not None:
        raise ConflictError("Категория с таким названием уже есть", code="DUPLICATE_CATEGORY")


async def create_category(
    session: AsyncSession, shop_id: UUID, data: MenuCategoryCreate
) -> MenuCategory:
    await _ensure_unique_category_name(session, shop_id, data.name)
    category = MenuCategory(coffee_shop_id=shop_id, name=data.name)
    session.add(category)
    await session.commit()
    return await _get_category_with_items(session, category.id)


async def _get_category_with_items(session: AsyncSession, category_id: UUID) -> MenuCategory:
    statement = (
        select(MenuCategory)
        .where(MenuCategory.id == category_id)
        .options(selectinload(MenuCategory.menu_items))
        .execution_options(populate_existing=True)
    )
    return (await session.scalars(statement)).one()


async def update_category(
    session: AsyncSession, shop_id: UUID, category_id: UUID, data: MenuCategoryUpdate
) -> MenuCategory:
    category = await _get_category(session, shop_id, category_id)
    await _ensure_unique_category_name(session, shop_id, data.name, exclude_id=category_id)
    category.name = data.name
    await session.commit()
    return await _get_category_with_items(session, category_id)


async def delete_category(session: AsyncSession, shop_id: UUID, category_id: UUID) -> None:
    """Удаляет только пустую категорию, чтобы позиции не пропали незаметно."""
    category = await _get_category(session, shop_id, category_id)
    has_items = await session.scalar(select(exists().where(MenuItem.category_id == category_id)))
    if has_items:
        raise ConflictError(
            "В категории есть позиции. Сначала удалите или перенесите их",
            code="CATEGORY_NOT_EMPTY",
        )
    await session.delete(category)
    await session.commit()


# ---------- Позиции ----------


async def get_item(session: AsyncSession, shop_id: UUID, item_id: UUID) -> MenuItem:
    item = await session.get(MenuItem, item_id)
    if item is None or item.coffee_shop_id != shop_id:
        raise NotFoundError("Позиция меню не найдена")
    return item


async def create_item(session: AsyncSession, shop_id: UUID, data: MenuItemCreate) -> MenuItem:
    await _get_category(session, shop_id, data.category_id)
    item = MenuItem(coffee_shop_id=shop_id, **data.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def update_item(
    session: AsyncSession, shop_id: UUID, item_id: UUID, data: MenuItemUpdate
) -> MenuItem:
    item = await get_item(session, shop_id, item_id)
    changes = data.model_dump(exclude_unset=True)
    if "category_id" in changes:
        await _get_category(session, shop_id, changes["category_id"])
    for field, value in changes.items():
        setattr(item, field, value)
    await session.flush()
    if "base_price" in changes:
        # Цена в открытых корзинах следует за меню; в оформленных заказах не меняется
        await carts.reprice_item(session, item)
    await session.commit()
    await session.refresh(item)
    return item


async def delete_item(session: AsyncSession, shop_id: UUID, item_id: UUID) -> None:
    """Удаляет позицию и убирает её из корзин.

    Если позиция есть в оформленных заказах, удаление запрещено: заказ должен
    сохранить свой состав. Такую позицию можно скрыть через is_available = false.
    """
    item = await get_item(session, shop_id, item_id)
    in_orders = await session.scalar(
        select(
            exists()
            .where(OrderItem.menu_item_id == item_id)
            .where(OrderItem.order_id == Order.id)
            .where(Order.status != "cart")
        )
    )
    if in_orders:
        raise ConflictError(
            "Позиция есть в оформленных заказах. Скройте её через is_available = false",
            code="ITEM_IN_ORDERS",
        )
    affected_carts = list(
        (
            await session.scalars(
                select(OrderItem.order_id).where(OrderItem.menu_item_id == item_id)
            )
        ).all()
    )
    await session.execute(delete(OrderItem).where(OrderItem.menu_item_id == item_id))
    await session.delete(item)
    await session.flush()
    await carts.recalculate_orders(session, affected_carts)
    await session.commit()
