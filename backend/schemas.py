import re
from datetime import datetime, time
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

# Схемы запросов и ответов API v1 (контракт: docs/api.md)

MAX_ITEM_QUANTITY = 50

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class OrderStatus(StrEnum):
    cart = "cart"
    pending = "pending"
    confirmed = "confirmed"
    ready = "ready"
    completed = "completed"
    cancelled = "cancelled"


class PatchModel(BaseModel):
    """Частичное обновление: явно переданный null запрещён для обязательных полей."""

    _required_fields: tuple[str, ...] = ()

    @model_validator(mode="after")
    def forbid_null_for_required(self):
        for field in self._required_fields:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Поле {field} не может быть пустым")
        return self


# ---------- Кофейни ----------


class CoffeeShopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    district: str | None = None
    opening_time: time
    closing_time: time
    address: str
    latitude: float
    longitude: float
    is_active: bool
    coffee_shop_image: str | None = None


class CoffeeShopOwnerView(CoffeeShopRead):
    owners: list[int]
    created_at: datetime


class CoffeeShopCreate(BaseModel):
    name: Name
    description: ShortText | None = None
    district: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    opening_time: time = Field(examples=["08:00"])
    closing_time: time = Field(examples=["22:00"])
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    is_active: bool = True
    coffee_shop_image: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check_hours(self):
        if self.opening_time == self.closing_time:
            raise ValueError("Время открытия и закрытия не может совпадать")
        return self


class CoffeeShopUpdate(PatchModel):
    _required_fields = (
        "name",
        "opening_time",
        "closing_time",
        "address",
        "latitude",
        "longitude",
        "is_active",
    )

    name: Name | None = None
    description: ShortText | None = None
    district: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    opening_time: time | None = None
    closing_time: time | None = None
    address: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        | None
    ) = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = None
    coffee_shop_image: str | None = Field(default=None, max_length=2000)


class OwnerAdd(BaseModel):
    telegram_id: int = Field(gt=0, description="Пользователь должен хоть раз войти в Mini App")


class OwnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    first_name: str
    username: str | None = None


# ---------- Меню ----------


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    name: str
    description: str | None = None
    base_price: int
    image_url: str | None = None
    is_available: bool


class MenuCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    items: list[MenuItemRead] = Field(default_factory=list, validation_alias="menu_items")


class MenuCategoryCreate(BaseModel):
    name: Name


class MenuCategoryUpdate(BaseModel):
    name: Name


class MenuItemCreate(BaseModel):
    category_id: UUID
    name: Name
    description: ShortText | None = None
    base_price: int = Field(ge=0, le=1_000_000, description="Цена в рублях")
    image_url: str | None = Field(default=None, max_length=2000)
    is_available: bool = True


class MenuItemUpdate(PatchModel):
    _required_fields = ("category_id", "name", "base_price", "is_available")

    category_id: UUID | None = None
    name: Name | None = None
    description: ShortText | None = None
    base_price: int | None = Field(default=None, ge=0, le=1_000_000)
    image_url: str | None = Field(default=None, max_length=2000)
    is_available: bool | None = None


# ---------- Профиль ----------


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool
    phone: str | None = None
    created_at: datetime


class UserUpdate(BaseModel):
    phone: str | None = Field(
        default=None,
        pattern=r"^\+\d{10,15}$",
        description="Телефон в международном формате, например +79990000001; null — удалить",
    )

    @field_validator("phone", mode="before")
    @classmethod
    def strip_formatting(cls, value):
        # "+7 (999) 000-00-01" -> "+79990000001"
        if isinstance(value, str):
            return re.sub(r"[\s()\-]", "", value)
        return value


# ---------- Время заказа ----------


class OrderTimeRead(BaseModel):
    order_time: datetime
    updated_at: datetime


class OrderTimeSet(BaseModel):
    order_time: AwareDatetime = Field(
        description="Желаемое время получения заказа с часовым поясом",
        examples=["2026-11-01T09:30:00+03:00"],
    )

    @field_validator("order_time")
    @classmethod
    def not_in_past(cls, value: datetime) -> datetime:
        if value < datetime.now(value.tzinfo):
            raise ValueError("Время заказа не может быть в прошлом")
        return value


# ---------- Избранное ----------


class FavoritesRead(BaseModel):
    coffee_shops: list[CoffeeShopRead] = Field(default_factory=list)


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
    items: list[OrderItemRead] = Field(default_factory=list)


class OrderRead(CartRead):
    telegram_id: int
    status: OrderStatus
    pickup_time: datetime | None = None
    created_at: datetime


class CartItemCreate(BaseModel):
    menu_item_id: UUID = Field(description="UUID позиции меню")
    quantity: int = Field(default=1, ge=1, le=MAX_ITEM_QUANTITY, description="Сколько добавить")


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=MAX_ITEM_QUANTITY, description="Новое количество")


class OrderCreate(BaseModel):
    coffee_shop_id: UUID = Field(description="Из корзины какой кофейни оформить заказ")
    pickup_time: AwareDatetime | None = Field(
        default=None,
        description="Время получения; если не передано, берётся из /me/order-time",
    )


class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(description="Новый статус заказа")
