from pydantic import BaseModel, Field, validator
from datetime import datetime
import re
from typing import List, Optional
from uuid import UUID
from datetime import time

class OrderTime(BaseModel):
    tg_id: int = Field(..., description="Telegram ID пользователя")
    date: str | None = Field(None, description="Время заказа в формате yyyy-mm-dd hh:mm:ss")
    action: str = Field(..., description="Действие - 'create', 'update', 'get', или 'delete'")

    @validator('date')
    def validate_order_time_format(cls, v):
        # Проверяем формат yyyy-mm-dd hh:mm:ss
        pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'
        if not re.match(pattern, v):
            raise ValueError('date должно быть в формате yyyy-mm-dd hh:mm:ss')
        return v
    
    @validator('action')
    def validate_action(cls, v):
        if v not in ['create', 'update', 'get', 'delete']:
            raise ValueError("action должно быть 'create', 'update', 'get', или 'delete'")
        return v
    
class CoffeeShopResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    owners: List[int]
    opening_time: time
    closing_time: time
    address: str
    latitude: float
    longitude: float
    is_active: bool
    coffee_shop_image: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True

class MenuItemResponse(BaseModel):
    id: UUID
    coffee_shop_id: UUID
    category_id: UUID
    name: str
    description: Optional[str] = None
    base_price: int
    image_url: Optional[str] = None
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MenuCategoryResponse(BaseModel):
    id: UUID
    coffee_shop_id: UUID
    name: str
    items: List[MenuItemResponse] = []

    class Config:
        from_attributes = True


class CoffeeShopMenu(BaseModel):
    coffee_shop_id: UUID = Field(..., description="UUID кофейни")

    @validator('coffee_shop_id')
    def validate_coffee_shop_id(cls, v):
        if not isinstance(v, UUID):
            raise ValueError('coffee_shop_id должно быть UUID')
        return v


class AddToCartRequest(BaseModel):
    tg_id: int = Field(..., description="Telegram ID пользователя")
    coffee_shop_id: UUID = Field(..., description="UUID кофейни")
    menu_item_id: UUID = Field(..., description="UUID пункта меню")
    quantity: int = Field(1, ge=-1, description="Количество товара")


class RemoveFromCartRequest(BaseModel):
    tg_id: int = Field(..., description="Telegram ID пользователя")
    order_item_id: UUID = Field(..., description="UUID товара в заказе")


class CartItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    menu_item_id: UUID
    quantity: int
    unit_price: int
    total_price: int
    product: MenuItemResponse
    
    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: UUID
    telegram_id: int
    coffee_shop_id: UUID
    status: str
    total_amount: int
    items: List[CartItemResponse] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


class FavoriteRequest(BaseModel):
    tg_id: int = Field(..., description="Telegram ID пользователя")
    coffee_shop_id: UUID = Field(..., description="UUID кофейни")


class FavoriteResponse(BaseModel):
    coffee_shops: List[CoffeeShopResponse] = []

    class Config:
        from_attributes = True
