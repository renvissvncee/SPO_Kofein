from typing import Annotated

from fastapi import FastAPI, Depends, Query
from schemas import OrderTime, CoffeeShopResponse, CoffeeShopMenu, MenuCategoryResponse, AddToCartRequest, RemoveFromCartRequest, CartResponse, FavoriteRequest, FavoriteResponse
from db.cache import crud_redis_time_order
from db.crud import get_all_coffee_shops, get_coffee_shop_menu as get_coffee_shop_menu_db, add_to_cart, remove_from_cart, get_cart, add_favorite, remove_favorite, get_favorites

from typing import List, Union

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/set_order_time")
async def set_order_time(data: OrderTime):
    result = await crud_redis_time_order(
        tg_id=data.tg_id,
        date=data.date,
        action=data.action
    )
    return result

@app.get("/coffee_shops", response_model=List[CoffeeShopResponse])
async def get_coffee_shops():
    shops = await get_all_coffee_shops()
    return shops

@app.get("/menu", response_model=List[MenuCategoryResponse])
async def get_coffee_shop_menu_handler(id: str = Query(..., description="ID кофейни")):
    categories = await get_coffee_shop_menu_db(id)
    return categories


@app.post("/favorites", response_model=FavoriteResponse)
async def add_favorite_handler(data: FavoriteRequest):
    favorite = await add_favorite(data.tg_id, data.coffee_shop_id)
    if favorite is None:
        return {"error": "Кофейня не найдена"}

    shops = await get_favorites(data.tg_id)
    return {"coffee_shops": shops}


@app.delete("/favorites")
async def remove_favorite_handler(tg_id: int, coffee_shop_id: str):
    from uuid import UUID
    ok = await remove_favorite(tg_id, UUID(coffee_shop_id))
    if not ok:
        return {"error": "Запись не найдена"}
    return {"status": "removed"}


@app.get("/favorites", response_model=FavoriteResponse)
async def get_favorites_handler(tg_id: int):
    shops = await get_favorites(tg_id)
    return {"coffee_shops": shops}


@app.post("/cart", response_model=Union[CartResponse, dict])
async def add_to_cart_handler(data: AddToCartRequest):
    cart = await add_to_cart(data.tg_id, data.coffee_shop_id, data.menu_item_id, data.quantity)
    if not cart:
        return {"error": "Товар не найден"}
    elif cart == "deleted":
        return {"message": "Корзина удалена"}
    return cart

@app.get("/cart")
async def get_cart_handler(tg_id: int, coffee_shop_id: str):
    from uuid import UUID
    cart = await get_cart(tg_id, UUID(coffee_shop_id))
    if not cart:
        return {"error": "Корзина пуста"}
    return cart


@app.delete("/cart")
async def remove_from_cart_handler(tg_id: int, order_item_id: str):
    from uuid import UUID
    cart = await remove_from_cart(tg_id, UUID(order_item_id))
    if cart is None:
        return {"error": "Товар не найден или корзина пуста"}
    return cart

