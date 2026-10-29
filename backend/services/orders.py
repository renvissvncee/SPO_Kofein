from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Order
from ..errors import ConflictError, NotFoundError
from ..schemas import OrderStatus
from . import carts, coffee_shops
from .order_time import OrderTimeStore

# Допустимые переходы статусов: (из, в) -> кто может выполнить
CUSTOMER = "customer"
OWNER = "owner"
TRANSITIONS: dict[tuple[OrderStatus, OrderStatus], frozenset[str]] = {
    (OrderStatus.pending, OrderStatus.confirmed): frozenset({OWNER}),
    (OrderStatus.pending, OrderStatus.cancelled): frozenset({CUSTOMER, OWNER}),
    (OrderStatus.confirmed, OrderStatus.ready): frozenset({OWNER}),
    (OrderStatus.confirmed, OrderStatus.cancelled): frozenset({OWNER}),
    (OrderStatus.ready, OrderStatus.completed): frozenset({OWNER}),
}


def check_transition(current: OrderStatus, new: OrderStatus, actor: str) -> None:
    allowed = TRANSITIONS.get((current, new), frozenset())
    if actor not in allowed:
        raise ConflictError(
            f"Переход статуса {current.value} → {new.value} недоступен",
            code="INVALID_STATUS_TRANSITION",
        )


def _orders_query():
    return select(Order).where(Order.status != "cart").order_by(Order.created_at.desc())


async def checkout(
    session: AsyncSession,
    telegram_id: int,
    shop_id: UUID,
    pickup_time: datetime | None,
    order_time_store: OrderTimeStore,
) -> Order:
    """Оформляет заказ из корзины: cart → pending."""
    shop = await coffee_shops.get_active(session, shop_id)
    cart = await carts.find_cart(session, telegram_id, shop_id)
    if cart is None or not cart.items:
        raise ConflictError("Корзина пуста", code="EMPTY_CART")

    unavailable = [
        {"menu_item_id": str(line.menu_item_id), "name": line.menu_item.name}
        for line in cart.items
        if not line.menu_item.is_available
    ]
    if unavailable:
        raise ConflictError(
            "Некоторых позиций нет в наличии, уберите их из корзины",
            code="ITEM_UNAVAILABLE",
            details=unavailable,
        )

    if pickup_time is None:
        stored = await order_time_store.get(telegram_id)
        pickup_time = stored["order_time"] if stored else None
    if pickup_time is not None:
        if pickup_time < datetime.now(UTC):
            raise ConflictError("Время получения уже прошло", code="PICKUP_TIME_PASSED")
        # Часы работы хранятся в местном времени, клиент передаёт время в своём поясе
        if not coffee_shops.is_open_at(shop, pickup_time.time()):
            raise ConflictError("Кофейня закрыта в выбранное время", code="SHOP_CLOSED")

    # Фиксируем актуальные цены меню на момент оформления
    for line in cart.items:
        line.unit_price = line.menu_item.base_price
        line.total_price = line.unit_price * line.quantity
    cart.total_amount = sum(line.total_price for line in cart.items)
    cart.status = OrderStatus.pending.value
    cart.pickup_time = pickup_time
    cart.created_at = datetime.now(UTC)
    await session.commit()
    await order_time_store.delete(telegram_id)
    return await carts.reload_order(session, cart.id)


async def list_for_customer(
    session: AsyncSession, telegram_id: int, status: OrderStatus | None = None
) -> list[Order]:
    statement = _orders_query().where(Order.telegram_id == telegram_id)
    if status is not None:
        statement = statement.where(Order.status == status.value)
    return list((await session.scalars(statement)).all())


async def get_for_customer(session: AsyncSession, telegram_id: int, order_id: UUID) -> Order:
    order = await session.get(Order, order_id)
    if order is None or order.telegram_id != telegram_id or order.status == "cart":
        raise NotFoundError("Заказ не найден")
    return order


async def list_for_shop(
    session: AsyncSession, shop_id: UUID, status: OrderStatus | None = None
) -> list[Order]:
    statement = _orders_query().where(Order.coffee_shop_id == shop_id)
    if status is not None:
        statement = statement.where(Order.status == status.value)
    return list((await session.scalars(statement)).all())


async def get_for_shop(session: AsyncSession, shop_id: UUID, order_id: UUID) -> Order:
    order = await session.get(Order, order_id)
    if order is None or order.coffee_shop_id != shop_id or order.status == "cart":
        raise NotFoundError("Заказ не найден")
    return order


async def change_status(
    session: AsyncSession, order: Order, new_status: OrderStatus, actor: str
) -> Order:
    check_transition(OrderStatus(order.status), new_status, actor)
    order.status = new_status.value
    await session.commit()
    return await carts.reload_order(session, order.id)
