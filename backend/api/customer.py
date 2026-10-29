"""Покупатель: свои данные, избранное, корзины и заказы. Нужен JWT.

Пользователь всегда берётся из токена, поэтому telegram_id в запросах не передаётся.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_authenticated_user
from ..db.models import session_dependency
from ..errors import NotFoundError, error_responses
from ..schemas import (
    CartItemCreate,
    CartItemUpdate,
    CartRead,
    FavoritesRead,
    OrderCreate,
    OrderRead,
    OrderStatus,
    OrderStatusUpdate,
    OrderTimeRead,
    OrderTimeSet,
    UserRead,
    UserUpdate,
)
from ..services import carts, favorites, orders, users
from ..services.order_time import OrderTimeStore, get_order_time_store

router = APIRouter(
    prefix="/me",
    dependencies=[Depends(require_authenticated_user)],
    responses=error_responses(401),
)

CurrentUser = Depends(require_authenticated_user)
Session = Depends(session_dependency)


# ---------- Профиль ----------


@router.get("", response_model=UserRead, tags=["Покупатель: профиль"], summary="Мой профиль")
async def get_profile(telegram_id: int = CurrentUser, session: AsyncSession = Session):
    return await users.get(session, telegram_id)


@router.patch(
    "",
    response_model=UserRead,
    tags=["Покупатель: профиль"],
    summary="Изменить профиль (телефон)",
    responses=error_responses(422),
)
async def update_profile(
    data: UserUpdate, telegram_id: int = CurrentUser, session: AsyncSession = Session
):
    return await users.update(session, telegram_id, data)


# ---------- Время заказа ----------


@router.get(
    "/order-time",
    response_model=OrderTimeRead,
    tags=["Покупатель: время заказа"],
    summary="Выбранное время получения",
    responses=error_responses(404),
)
async def get_order_time(
    telegram_id: int = CurrentUser, store: OrderTimeStore = Depends(get_order_time_store)
):
    record = await store.get(telegram_id)
    if record is None:
        raise NotFoundError("Время заказа не выбрано")
    return record


@router.put(
    "/order-time",
    response_model=OrderTimeRead,
    tags=["Покупатель: время заказа"],
    summary="Выбрать или изменить время получения",
    responses=error_responses(422),
)
async def set_order_time(
    data: OrderTimeSet,
    telegram_id: int = CurrentUser,
    store: OrderTimeStore = Depends(get_order_time_store),
):
    return await store.set(telegram_id, data.order_time)


@router.delete(
    "/order-time",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Покупатель: время заказа"],
    summary="Сбросить время получения",
    responses=error_responses(404),
)
async def delete_order_time(
    telegram_id: int = CurrentUser, store: OrderTimeStore = Depends(get_order_time_store)
) -> None:
    if not await store.delete(telegram_id):
        raise NotFoundError("Время заказа не выбрано")


# ---------- Избранное ----------


@router.get(
    "/favorites",
    response_model=FavoritesRead,
    tags=["Покупатель: избранное"],
    summary="Избранные кофейни",
)
async def list_favorites(telegram_id: int = CurrentUser, session: AsyncSession = Session):
    return {"coffee_shops": await favorites.list_shops(session, telegram_id)}


@router.put(
    "/favorites/{shop_id}",
    response_model=FavoritesRead,
    tags=["Покупатель: избранное"],
    summary="Добавить кофейню в избранное",
    responses={
        201: {"description": "Кофейня добавлена", "model": FavoritesRead},
        **error_responses(404, 422),
    },
)
async def add_favorite(
    shop_id: UUID,
    response: Response,
    telegram_id: int = CurrentUser,
    session: AsyncSession = Session,
):
    created = await favorites.add(session, telegram_id, shop_id)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return {"coffee_shops": await favorites.list_shops(session, telegram_id)}


@router.delete(
    "/favorites/{shop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Покупатель: избранное"],
    summary="Убрать кофейню из избранного",
    responses=error_responses(404, 422),
)
async def remove_favorite(
    shop_id: UUID, telegram_id: int = CurrentUser, session: AsyncSession = Session
) -> None:
    await favorites.remove(session, telegram_id, shop_id)


# ---------- Корзины ----------


@router.get(
    "/carts",
    response_model=list[CartRead],
    tags=["Покупатель: корзина"],
    summary="Все мои корзины",
)
async def list_carts(telegram_id: int = CurrentUser, session: AsyncSession = Session):
    return await carts.list_carts(session, telegram_id)


@router.get(
    "/carts/{shop_id}",
    response_model=CartRead,
    tags=["Покупатель: корзина"],
    summary="Корзина в кофейне",
    responses=error_responses(404, 422),
)
async def get_cart(shop_id: UUID, telegram_id: int = CurrentUser, session: AsyncSession = Session):
    return await carts.get_cart(session, telegram_id, shop_id)


@router.post(
    "/carts/{shop_id}/items",
    response_model=CartRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Покупатель: корзина"],
    summary="Добавить позицию в корзину",
    responses={
        200: {"description": "Позиция уже была, количество увеличено", "model": CartRead},
        **error_responses(404, 409, 422),
    },
)
async def add_cart_item(
    shop_id: UUID,
    data: CartItemCreate,
    response: Response,
    telegram_id: int = CurrentUser,
    session: AsyncSession = Session,
):
    cart, created = await carts.add_item(
        session, telegram_id, shop_id, data.menu_item_id, data.quantity
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return cart


@router.patch(
    "/carts/{shop_id}/items/{menu_item_id}",
    response_model=CartRead,
    tags=["Покупатель: корзина"],
    summary="Изменить количество позиции",
    responses=error_responses(404, 422),
)
async def update_cart_item(
    shop_id: UUID,
    menu_item_id: UUID,
    data: CartItemUpdate,
    telegram_id: int = CurrentUser,
    session: AsyncSession = Session,
):
    return await carts.set_quantity(session, telegram_id, shop_id, menu_item_id, data.quantity)


@router.delete(
    "/carts/{shop_id}/items/{menu_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Покупатель: корзина"],
    summary="Убрать позицию из корзины",
    responses=error_responses(404, 422),
)
async def remove_cart_item(
    shop_id: UUID,
    menu_item_id: UUID,
    telegram_id: int = CurrentUser,
    session: AsyncSession = Session,
) -> None:
    await carts.remove_item(session, telegram_id, shop_id, menu_item_id)


@router.delete(
    "/carts/{shop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Покупатель: корзина"],
    summary="Очистить корзину",
    responses=error_responses(404, 422),
)
async def clear_cart(
    shop_id: UUID, telegram_id: int = CurrentUser, session: AsyncSession = Session
) -> None:
    await carts.clear(session, telegram_id, shop_id)


# ---------- Заказы ----------


@router.post(
    "/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Покупатель: заказы"],
    summary="Оформить заказ из корзины",
    responses=error_responses(404, 409, 422),
)
async def create_order(
    data: OrderCreate,
    telegram_id: int = CurrentUser,
    session: AsyncSession = Session,
    store: OrderTimeStore = Depends(get_order_time_store),
):
    return await orders.checkout(session, telegram_id, data.coffee_shop_id, data.pickup_time, store)


@router.get(
    "/orders",
    response_model=list[OrderRead],
    tags=["Покупатель: заказы"],
    summary="История заказов",
    responses=error_responses(422),
)
async def list_orders(
    status: OrderStatus | None = None,
    telegram_id: int = CurrentUser,
    session: AsyncSession = Session,
):
    return await orders.list_for_customer(session, telegram_id, status)


@router.get(
    "/orders/{order_id}",
    response_model=OrderRead,
    tags=["Покупатель: заказы"],
    summary="Один заказ",
    responses=error_responses(404, 422),
)
async def get_order(
    order_id: UUID, telegram_id: int = CurrentUser, session: AsyncSession = Session
):
    return await orders.get_for_customer(session, telegram_id, order_id)


@router.patch(
    "/orders/{order_id}",
    response_model=OrderRead,
    tags=["Покупатель: заказы"],
    summary="Отменить заказ",
    responses=error_responses(404, 409, 422),
)
async def cancel_order(
    order_id: UUID,
    data: OrderStatusUpdate,
    telegram_id: int = CurrentUser,
    session: AsyncSession = Session,
):
    order = await orders.get_for_customer(session, telegram_id, order_id)
    return await orders.change_status(session, order, data.status, orders.CUSTOMER)
