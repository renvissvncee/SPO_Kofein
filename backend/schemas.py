from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CoffeeShopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    owners: list[int]
    opening_time: time
    closing_time: time
    address: str
    latitude: float
    longitude: float
    is_active: bool
    coffee_shop_image: str | None = None
    created_at: datetime


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    coffee_shop_id: UUID
    category_id: UUID
    name: str
    description: str | None = None
    base_price: int
    image_url: str | None = None
    is_available: bool
    created_at: datetime


class MenuCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    coffee_shop_id: UUID
    name: str
    items: list[MenuItemResponse] = Field(default_factory=list)


class CoffeeShopMenu(BaseModel):
    coffee_shop_id: UUID = Field(description="Coffee shop UUID")


class AddToCartRequest(BaseModel):
    coffee_shop_id: UUID = Field(description="Coffee shop UUID")
    menu_item_id: UUID = Field(description="Menu item UUID")
    quantity: int = Field(1, ge=-1, description="Quantity change")

    @field_validator("quantity")
    @classmethod
    def quantity_must_not_be_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity must not be zero")
        return value


class RemoveFromCartRequest(BaseModel):
    order_item_id: UUID = Field(description="Order item UUID")


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    menu_item_id: UUID
    quantity: int
    unit_price: int
    total_price: int
    product: MenuItemResponse


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_id: int
    coffee_shop_id: UUID
    status: str
    total_amount: int
    items: list[CartItemResponse] = Field(default_factory=list)
    created_at: datetime


class FavoriteRequest(BaseModel):
    coffee_shop_id: UUID = Field(description="Coffee shop UUID")


class FavoriteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    coffee_shops: list[CoffeeShopResponse] = Field(default_factory=list)
