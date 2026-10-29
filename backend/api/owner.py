"""Владелец кофейни: управление кофейней, меню, владельцами и заказами.

Эндпоинты с {shop_id} доступны только владельцам этой кофейни (иначе 403).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_authenticated_user, require_coffee_shop_owner
from ..db.models import session_dependency
from ..errors import error_responses
from ..schemas import (
    CoffeeShopCreate,
    CoffeeShopOwnerView,
    CoffeeShopUpdate,
    MenuCategoryCreate,
    MenuCategoryRead,
    MenuCategoryUpdate,
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    OrderRead,
    OrderStatus,
    OrderStatusUpdate,
    OwnerAdd,
    OwnerRead,
)
from ..services import coffee_shops, menu, orders

router = APIRouter(responses=error_responses(401))

Session = Depends(session_dependency)
Owner = Depends(require_coffee_shop_owner)
owner_errors = error_responses(403, 404, 422)


# ---------- Кофейни ----------


@router.get(
    "/me/coffee-shops",
    response_model=list[CoffeeShopOwnerView],
    tags=["Владелец: кофейни"],
    summary="Мои кофейни (включая скрытые)",
)
async def list_my_coffee_shops(
    telegram_id: int = Depends(require_authenticated_user), session: AsyncSession = Session
):
    return await coffee_shops.list_owned(session, telegram_id)


@router.post(
    "/coffee-shops",
    response_model=CoffeeShopOwnerView,
    status_code=status.HTTP_201_CREATED,
    tags=["Владелец: кофейни"],
    summary="Создать кофейню (создатель становится владельцем)",
    responses=error_responses(422),
)
async def create_coffee_shop(
    data: CoffeeShopCreate,
    telegram_id: int = Depends(require_authenticated_user),
    session: AsyncSession = Session,
):
    return await coffee_shops.create(session, telegram_id, data)


@router.get(
    "/coffee-shops/{shop_id}/manage",
    response_model=CoffeeShopOwnerView,
    tags=["Владелец: кофейни"],
    summary="Кофейня для владельца (в том числе скрытая)",
    responses=owner_errors,
)
async def get_owned_coffee_shop(shop_id: UUID, _: int = Owner, session: AsyncSession = Session):
    return await coffee_shops.get_any(session, shop_id)


@router.patch(
    "/coffee-shops/{shop_id}",
    response_model=CoffeeShopOwnerView,
    tags=["Владелец: кофейни"],
    summary="Изменить кофейню",
    responses={**owner_errors, **error_responses(409)},
)
async def update_coffee_shop(
    shop_id: UUID, data: CoffeeShopUpdate, _: int = Owner, session: AsyncSession = Session
):
    return await coffee_shops.update(session, shop_id, data)


@router.delete(
    "/coffee-shops/{shop_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Владелец: кофейни"],
    summary="Удалить кофейню",
    responses={**owner_errors, **error_responses(409)},
)
async def delete_coffee_shop(
    shop_id: UUID, _: int = Owner, session: AsyncSession = Session
) -> None:
    await coffee_shops.remove(session, shop_id)


# ---------- Владельцы ----------


@router.get(
    "/coffee-shops/{shop_id}/owners",
    response_model=list[OwnerRead],
    tags=["Владелец: совладельцы"],
    summary="Владельцы кофейни",
    responses=owner_errors,
)
async def list_owners(shop_id: UUID, _: int = Owner, session: AsyncSession = Session):
    return await coffee_shops.list_owners(session, shop_id)


@router.post(
    "/coffee-shops/{shop_id}/owners",
    response_model=OwnerRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Владелец: совладельцы"],
    summary="Добавить владельца",
    responses=owner_errors,
)
async def add_owner(shop_id: UUID, data: OwnerAdd, _: int = Owner, session: AsyncSession = Session):
    return await coffee_shops.add_owner(session, shop_id, data.telegram_id)


@router.delete(
    "/coffee-shops/{shop_id}/owners/{telegram_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Владелец: совладельцы"],
    summary="Удалить владельца",
    responses={**owner_errors, **error_responses(409)},
)
async def remove_owner(
    shop_id: UUID, telegram_id: int, _: int = Owner, session: AsyncSession = Session
) -> None:
    await coffee_shops.remove_owner(session, shop_id, telegram_id)


# ---------- Категории меню ----------


@router.post(
    "/coffee-shops/{shop_id}/menu/categories",
    response_model=MenuCategoryRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Владелец: меню"],
    summary="Добавить категорию",
    responses={**owner_errors, **error_responses(409)},
)
async def create_category(
    shop_id: UUID, data: MenuCategoryCreate, _: int = Owner, session: AsyncSession = Session
):
    return await menu.create_category(session, shop_id, data)


@router.patch(
    "/coffee-shops/{shop_id}/menu/categories/{category_id}",
    response_model=MenuCategoryRead,
    tags=["Владелец: меню"],
    summary="Переименовать категорию",
    responses={**owner_errors, **error_responses(409)},
)
async def update_category(
    shop_id: UUID,
    category_id: UUID,
    data: MenuCategoryUpdate,
    _: int = Owner,
    session: AsyncSession = Session,
):
    return await menu.update_category(session, shop_id, category_id, data)


@router.delete(
    "/coffee-shops/{shop_id}/menu/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Владелец: меню"],
    summary="Удалить пустую категорию",
    responses={**owner_errors, **error_responses(409)},
)
async def delete_category(
    shop_id: UUID, category_id: UUID, _: int = Owner, session: AsyncSession = Session
) -> None:
    await menu.delete_category(session, shop_id, category_id)


# ---------- Позиции меню ----------


@router.post(
    "/coffee-shops/{shop_id}/menu/items",
    response_model=MenuItemRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Владелец: меню"],
    summary="Добавить позицию",
    responses=owner_errors,
)
async def create_item(
    shop_id: UUID, data: MenuItemCreate, _: int = Owner, session: AsyncSession = Session
):
    return await menu.create_item(session, shop_id, data)


@router.patch(
    "/coffee-shops/{shop_id}/menu/items/{item_id}",
    response_model=MenuItemRead,
    tags=["Владелец: меню"],
    summary="Изменить позицию (цена, наличие, категория…)",
    responses=owner_errors,
)
async def update_item(
    shop_id: UUID,
    item_id: UUID,
    data: MenuItemUpdate,
    _: int = Owner,
    session: AsyncSession = Session,
):
    return await menu.update_item(session, shop_id, item_id, data)


@router.delete(
    "/coffee-shops/{shop_id}/menu/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Владелец: меню"],
    summary="Удалить позицию",
    responses={**owner_errors, **error_responses(409)},
)
async def delete_item(
    shop_id: UUID, item_id: UUID, _: int = Owner, session: AsyncSession = Session
) -> None:
    await menu.delete_item(session, shop_id, item_id)


# ---------- Заказы кофейни ----------


@router.get(
    "/coffee-shops/{shop_id}/orders",
    response_model=list[OrderRead],
    tags=["Владелец: заказы"],
    summary="Заказы кофейни",
    responses=owner_errors,
)
async def list_shop_orders(
    shop_id: UUID,
    status: OrderStatus | None = None,
    _: int = Owner,
    session: AsyncSession = Session,
):
    return await orders.list_for_shop(session, shop_id, status)


@router.get(
    "/coffee-shops/{shop_id}/orders/{order_id}",
    response_model=OrderRead,
    tags=["Владелец: заказы"],
    summary="Один заказ кофейни",
    responses=owner_errors,
)
async def get_shop_order(
    shop_id: UUID, order_id: UUID, _: int = Owner, session: AsyncSession = Session
):
    return await orders.get_for_shop(session, shop_id, order_id)


@router.patch(
    "/coffee-shops/{shop_id}/orders/{order_id}",
    response_model=OrderRead,
    tags=["Владелец: заказы"],
    summary="Сменить статус заказа",
    responses={**owner_errors, **error_responses(409)},
)
async def update_shop_order_status(
    shop_id: UUID,
    order_id: UUID,
    data: OrderStatusUpdate,
    _: int = Owner,
    session: AsyncSession = Session,
):
    order = await orders.get_for_shop(session, shop_id, order_id)
    return await orders.change_status(session, order, data.status, orders.OWNER)
