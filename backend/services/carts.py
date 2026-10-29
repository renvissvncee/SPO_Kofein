"""Корзина: заказ в статусе cart, не больше одного на пользователя и кофейню.

Позиции корзины адресуются по menu_item_id: одна позиция меню встречается
в корзине один раз (ограничение uq_order_item_menu_item).
Пустая корзина удаляется.
"""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import MenuItem, Order, OrderItem
from ..errors import ConflictError, NotFoundError
from ..schemas import MAX_ITEM_QUANTITY
from . import coffee_shops


def _cart_query(telegram_id: int):
    return select(Order).where(Order.telegram_id == telegram_id, Order.status == "cart")


async def list_carts(session: AsyncSession, telegram_id: int) -> list[Order]:
    statement = _cart_query(telegram_id).order_by(Order.created_at)
    return list((await session.scalars(statement)).all())


async def find_cart(session: AsyncSession, telegram_id: int, shop_id: UUID) -> Order | None:
    statement = _cart_query(telegram_id).where(Order.coffee_shop_id == shop_id)
    return (await session.scalars(statement)).one_or_none()


async def get_cart(session: AsyncSession, telegram_id: int, shop_id: UUID) -> Order:
    cart = await find_cart(session, telegram_id, shop_id)
    if cart is None:
        raise NotFoundError("Корзина пуста")
    return cart


async def reload_order(session: AsyncSession, order_id: UUID) -> Order:
    """Перечитывает заказ вместе с позициями (после commit они устаревают)."""
    statement = select(Order).where(Order.id == order_id).execution_options(populate_existing=True)
    return (await session.scalars(statement)).one()


def _recalculate(order: Order) -> None:
    for item in order.items:
        item.total_price = item.unit_price * item.quantity
    order.total_amount = sum(item.total_price for item in order.items)


def _find_line(cart: Order, menu_item_id: UUID) -> OrderItem:
    for line in cart.items:
        if line.menu_item_id == menu_item_id:
            return line
    raise NotFoundError("Позиции нет в корзине")


async def add_item(
    session: AsyncSession, telegram_id: int, shop_id: UUID, menu_item_id: UUID, quantity: int
) -> tuple[Order, bool]:
    """Добавляет позицию или увеличивает количество. Возвращает корзину и
    признак того, что позиция добавлена впервые."""
    await coffee_shops.get_active(session, shop_id)
    menu_item = await session.get(MenuItem, menu_item_id)
    if menu_item is None or menu_item.coffee_shop_id != shop_id:
        raise NotFoundError("Позиция меню не найдена в этой кофейне")
    if not menu_item.is_available:
        raise ConflictError("Позиции сейчас нет в наличии", code="ITEM_UNAVAILABLE")

    cart = await find_cart(session, telegram_id, shop_id)
    if cart is None:
        cart = Order(telegram_id=telegram_id, coffee_shop_id=shop_id, status="cart", total_amount=0)
        session.add(cart)
        await session.flush()
        await session.refresh(cart, ["items"])

    created = False
    try:
        line = _find_line(cart, menu_item_id)
        line.quantity += quantity
    except NotFoundError:
        created = True
        line = OrderItem(
            menu_item_id=menu_item_id,
            quantity=quantity,
            unit_price=menu_item.base_price,
            total_price=0,
        )
        cart.items.append(line)
    if line.quantity > MAX_ITEM_QUANTITY:
        raise ConflictError(
            f"Нельзя заказать больше {MAX_ITEM_QUANTITY} штук одной позиции",
            code="QUANTITY_LIMIT",
        )
    _recalculate(cart)
    await session.commit()
    return await reload_order(session, cart.id), created


async def set_quantity(
    session: AsyncSession, telegram_id: int, shop_id: UUID, menu_item_id: UUID, quantity: int
) -> Order:
    cart = await get_cart(session, telegram_id, shop_id)
    _find_line(cart, menu_item_id).quantity = quantity
    _recalculate(cart)
    await session.commit()
    return await reload_order(session, cart.id)


async def remove_item(
    session: AsyncSession, telegram_id: int, shop_id: UUID, menu_item_id: UUID
) -> None:
    cart = await get_cart(session, telegram_id, shop_id)
    cart.items.remove(_find_line(cart, menu_item_id))
    if cart.items:
        _recalculate(cart)
    else:
        await session.delete(cart)
    await session.commit()


async def clear(session: AsyncSession, telegram_id: int, shop_id: UUID) -> None:
    cart = await get_cart(session, telegram_id, shop_id)
    await session.delete(cart)
    await session.commit()


async def reprice_item(session: AsyncSession, menu_item: MenuItem) -> None:
    """Обновляет цену позиции во всех корзинах (без commit)."""
    statement = (
        select(Order)
        .join(OrderItem)
        .where(OrderItem.menu_item_id == menu_item.id, Order.status == "cart")
    )
    for cart in (await session.scalars(statement)).unique():
        for line in cart.items:
            if line.menu_item_id == menu_item.id:
                line.unit_price = menu_item.base_price
        _recalculate(cart)


async def recalculate_orders(session: AsyncSession, order_ids: Iterable[UUID]) -> None:
    """Пересчитывает суммы корзин и удаляет опустевшие (без commit)."""
    for order_id in set(order_ids):
        cart = await reload_order(session, order_id)
        if cart.items:
            _recalculate(cart)
        else:
            await session.delete(cart)
