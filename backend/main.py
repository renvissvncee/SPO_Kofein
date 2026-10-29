from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth import JWTAuthenticationMiddleware, require_authenticated_user, router as auth_router
from .config import get_settings
from .db.crud import (
    add_favorite,
    add_to_cart,
    get_all_coffee_shops,
    get_cart,
    get_coffee_shop_menu,
    get_favorites,
    remove_favorite,
    remove_from_cart,
)
from .schemas import (
    AddToCartRequest,
    CartResponse,
    CoffeeShopResponse,
    FavoriteRequest,
    FavoriteResponse,
    MenuCategoryResponse,
)


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_auth()
    yield


app = FastAPI(title="Kofein API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(JWTAuthenticationMiddleware)
app.include_router(auth_router)
app.mount(
    "/mini-app",
    StaticFiles(directory=Path(__file__).parent / "static", html=True),
    name="mini-app",
)



@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/coffee_shops", response_model=list[CoffeeShopResponse])
async def coffee_shops():
    return await get_all_coffee_shops()


@app.get("/menu", response_model=list[MenuCategoryResponse])
async def coffee_shop_menu(
    coffee_shop_id: UUID = Query(alias="id", description="Coffee shop UUID"),
):
    return await get_coffee_shop_menu(coffee_shop_id)


@app.post("/favorites", response_model=FavoriteResponse)
async def add_favorite_handler(
    data: FavoriteRequest,
    telegram_id: int = Depends(require_authenticated_user),
):
    favorite = await add_favorite(telegram_id, data.coffee_shop_id)
    if favorite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coffee shop not found",
        )
    shops = await get_favorites(telegram_id)
    return {"coffee_shops": shops}


@app.delete("/favorites", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_handler(
    coffee_shop_id: UUID,
    telegram_id: int = Depends(require_authenticated_user),
) -> None:
    removed = await remove_favorite(telegram_id, coffee_shop_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found",
        )


@app.get("/favorites", response_model=FavoriteResponse)
async def get_favorites_handler(
    telegram_id: int = Depends(require_authenticated_user),
):
    shops = await get_favorites(telegram_id)
    return {"coffee_shops": shops}


@app.post("/cart", response_model=CartResponse)
async def add_to_cart_handler(
    data: AddToCartRequest,
    telegram_id: int = Depends(require_authenticated_user),
):
    cart = await add_to_cart(
        telegram_id,
        data.coffee_shop_id,
        data.menu_item_id,
        data.quantity,
    )
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found in this coffee shop",
        )
    if cart == "deleted":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart is empty",
        )
    return cart


@app.get("/cart", response_model=CartResponse)
async def get_cart_handler(
    coffee_shop_id: UUID,
    telegram_id: int = Depends(require_authenticated_user),
):
    cart = await get_cart(telegram_id, coffee_shop_id)
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart is empty",
        )
    return cart


@app.delete("/cart", response_model=CartResponse)
async def remove_from_cart_handler(
    order_item_id: UUID,
    telegram_id: int = Depends(require_authenticated_user),
):
    cart = await remove_from_cart(telegram_id, order_item_id)
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found or cart is empty",
        )
    return cart
