"""Публичная часть: доступна без аутентификации (гость)."""

from datetime import time
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import session_dependency
from ..errors import error_responses
from ..schemas import CoffeeShopRead, MenuCategoryRead, MenuItemRead
from ..services import coffee_shops, menu

router = APIRouter(tags=["Публичное: кофейни и меню"])


@router.get(
    "/coffee-shops",
    response_model=list[CoffeeShopRead],
    summary="Список и поиск кофеен",
    responses=error_responses(422),
)
async def list_coffee_shops(
    q: str | None = Query(None, max_length=100, description="Поиск по названию, адресу или району"),
    district: str | None = Query(None, max_length=100, description="Точное совпадение района"),
    open_at: time | None = Query(None, description="Только открытые в это время, HH:MM"),
    session: AsyncSession = Depends(session_dependency),
):
    return await coffee_shops.list_public(session, q, district, open_at)


@router.get(
    "/coffee-shops/{shop_id}",
    response_model=CoffeeShopRead,
    summary="Страница кофейни",
    responses=error_responses(404, 422),
)
async def get_coffee_shop(shop_id: UUID, session: AsyncSession = Depends(session_dependency)):
    return await coffee_shops.get_active(session, shop_id)


@router.get(
    "/coffee-shops/{shop_id}/menu",
    response_model=list[MenuCategoryRead],
    summary="Меню кофейни по категориям",
    responses=error_responses(404, 422),
)
async def get_menu(shop_id: UUID, session: AsyncSession = Depends(session_dependency)):
    await coffee_shops.get_active(session, shop_id)
    return await menu.get_menu(session, shop_id)


@router.get(
    "/coffee-shops/{shop_id}/menu/items/{item_id}",
    response_model=MenuItemRead,
    summary="Одна позиция меню",
    responses=error_responses(404, 422),
)
async def get_menu_item(
    shop_id: UUID, item_id: UUID, session: AsyncSession = Depends(session_dependency)
):
    await coffee_shops.get_active(session, shop_id)
    return await menu.get_item(session, shop_id, item_id)
