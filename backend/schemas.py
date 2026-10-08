import re
from datetime import datetime, time
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ================================================================
# Старые схемы — используются текущими эндпоинтами в main.py.
# Будут удалены, когда эндпоинты перейдут на схемы API v1 (этап 5).
# ================================================================


class OrderTime(BaseModel):
    tg_id: int = Field(description="Telegram ID пользователя")
    date: str | None = Field(default=None, description="Время заказа в формате yyyy-mm-dd hh:mm:ss")
    action: Literal["create", "update", "get", "delete"] = Field(
        description="Действие - 'create', 'update', 'get', или 'delete'"
    )

    @field_validator("date")
    @classmethod
    def validate_order_time_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("date должно быть в формате yyyy-mm-dd hh:mm:ss")
        return v

    @model_validator(mode="after")
    def date_required_for_write(self) -> "OrderTime":
        if self.action in ("create", "update") and self.date is None:
            raise ValueError(f"date обязательно для action='{self.action}'")
        return self


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
    is_active: bool | None = None
    coffee_shop_image: str | None = None
    created_at: datetime | None = None


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    coffee_shop_id: UUID
    category_id: UUID
    name: str
    description: str | None = None
    base_price: int
    image_url: str | None = None
    is_available: bool | None = None
    created_at: datetime | None = None


class MenuCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    coffee_shop_id: UUID
    name: str
    items: list[MenuItemResponse] = []


class CoffeeShopMenu(BaseModel):
    coffee_shop_id: UUID = Field(description="UUID кофейни")


class AddToCartRequest(BaseModel):
    tg_id: int = Field(description="Telegram ID пользователя")
    coffee_shop_id: UUID = Field(description="UUID кофейни")
    menu_item_id: UUID = Field(description="UUID пункта меню")
    quantity: int = Field(default=1, ge=-1, description="Количество товара")


class RemoveFromCartRequest(BaseModel):
    tg_id: int = Field(description="Telegram ID пользователя")
    order_item_id: UUID = Field(description="UUID товара в заказе")


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
    items: list[CartItemResponse] = []
    created_at: datetime | None = None


class FavoriteRequest(BaseModel):
    tg_id: int = Field(description="Telegram ID пользователя")
    coffee_shop_id: UUID = Field(description="UUID кофейни")


class FavoriteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    coffee_shops: list[CoffeeShopResponse] = []


# ================================================================
# Схемы API v1 (по контракту docs/api.md)
# ================================================================

MAX_ITEM_QUANTITY = 50


class OrderStatus(str, Enum):
    cart = "cart"
    pending = "pending"
    confirmed = "confirmed"
    ready = "ready"
    completed = "completed"
    cancelled = "cancelled"


# ---------- Кофейни и меню ----------


class CoffeeShopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    opening_time: time
    closing_time: time
    address: str
    latitude: float
    longitude: float
    is_active: bool | None = None
    coffee_shop_image: str | None = None


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    name: str
    description: str | None = None
    base_price: int
    image_url: str | None = None
    is_available: bool | None = None


class MenuCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    items: list[MenuItemRead] = Field(default=[], validation_alias="menu_items")


# ---------- Профиль ----------


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    phone: str | None = None
    created_at: datetime | None = None


class UserUpdate(BaseModel):
    phone: str | None = Field(
        default=None,
        pattern=r"^\+\d{10,15}$",
        description="Телефон в международном формате, например +79990000001",
    )

    @field_validator("phone", mode="before")
    @classmethod
    def strip_formatting(cls, v):
        # "+7 (999) 000-00-01" -> "+79990000001"
        if isinstance(v, str):
            return re.sub(r"[\s()\-]", "", v)
        return v


# ---------- Время заказа ----------


class OrderTimeRead(BaseModel):
    order_time: datetime
    updated_at: datetime


class OrderTimeSet(BaseModel):
    order_time: datetime = Field(description="Желаемое время получения заказа")

    @field_validator("order_time")
    @classmethod
    def not_in_past(cls, v: datetime) -> datetime:
        now = datetime.now(v.tzinfo)
        if v < now:
            raise ValueError("Время заказа не может быть в прошлом")
        return v


# ---------- Корзина и заказы ----------


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    menu_item_id: UUID
    quantity: int
    unit_price: int
    total_price: int
    menu_item: MenuItemRead


class CartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    coffee_shop_id: UUID
    total_amount: int
    items: list[OrderItemRead] = []


class OrderRead(CartRead):
    status: OrderStatus
    created_at: datetime | None = None


class CartItemCreate(BaseModel):
    menu_item_id: UUID = Field(description="UUID позиции меню")
    quantity: int = Field(default=1, ge=1, le=MAX_ITEM_QUANTITY, description="Сколько добавить")


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=MAX_ITEM_QUANTITY, description="Новое количество")


class OrderCreate(BaseModel):
    coffee_shop_id: UUID = Field(description="Из корзины какой кофейни оформить заказ")


class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(description="Новый статус заказа")
