import uuid
from datetime import datetime, time
from typing import List
from contextlib import asynccontextmanager

from sqlalchemy import (
    BigInteger, String, Text, DateTime, Boolean, Time, DECIMAL, Integer,
    ForeignKey, UniqueConstraint, CheckConstraint, func, text
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

DATABASE_URL = "postgresql+asyncpg://postgres:busilda1981@localhost:5432/caffein"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

class Base(DeclarativeBase):
    pass


# Статусы заказа (жизненный цикл):
# cart — корзина, заказ ещё не оформлен;
# pending — оформлен, ждёт подтверждения кофейни;
# confirmed — кофейня приняла заказ и готовит;
# ready — готов, можно забирать;
# completed — выдан;
# cancelled — отменён.
ORDER_STATUSES = ("cart", "pending", "confirmed", "ready", "completed", "cancelled")
_ORDER_STATUSES_SQL = ", ".join(f"'{s}'" for s in ORDER_STATUSES)


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders = relationship("Order", back_populates="user")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    owned_coffee_shops = relationship("CoffeeShopOwner", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)


class CoffeeShop(Base):
    __tablename__ = "coffee_shops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    opening_time: Mapped[time] = mapped_column(Time, nullable=False)
    closing_time: Mapped[time] = mapped_column(Time, nullable=False)

    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(DECIMAL(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(DECIMAL(9, 6), nullable=False)

    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    coffee_shop_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    categories = relationship("MenuCategory", back_populates="coffee_shop", cascade="all, delete-orphan", passive_deletes=True)
    menu_items = relationship("MenuItem", back_populates="coffee_shop", cascade="all, delete-orphan", passive_deletes=True)
    orders = relationship("Order", back_populates="coffee_shop")
    favorites = relationship("Favorite", back_populates="coffee_shop", cascade="all, delete-orphan", passive_deletes=True)
    owner_links = relationship("CoffeeShopOwner", back_populates="coffee_shop", cascade="all, delete-orphan", passive_deletes=True, lazy="selectin")

    @property
    def owners(self) -> List[int]:
        """telegram_id владельцев (из таблицы coffee_shop_owners)."""
        return [link.telegram_id for link in self.owner_links]


class CoffeeShopOwner(Base):
    """Связь многие-ко-многим пользователей и кофеен (владельцы)."""
    __tablename__ = "coffee_shop_owners"

    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coffee_shops.id", ondelete="CASCADE"), primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)

    coffee_shop = relationship("CoffeeShop", back_populates="owner_links")
    user = relationship("User", back_populates="owned_coffee_shops")


class MenuCategory(Base):
    __tablename__ = "menu_categories"
    __table_args__ = (
        UniqueConstraint("coffee_shop_id", "name", name="uq_menu_category_shop_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coffee_shops.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    coffee_shop = relationship("CoffeeShop", back_populates="categories")
    menu_items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan", passive_deletes=True)


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (
        CheckConstraint("base_price >= 0", name="ck_menu_item_base_price"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coffee_shops.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("menu_categories.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool | None] = mapped_column(Boolean, default=True, server_default=text("TRUE"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    coffee_shop = relationship("CoffeeShop", back_populates="menu_items")
    category = relationship("MenuCategory", back_populates="menu_items")
    order_items = relationship("OrderItem", back_populates="menu_item")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_order_total_amount"),
        CheckConstraint(f"status IN ({_ORDER_STATUSES_SQL})", name="ck_order_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coffee_shops.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default=text("'pending'"))
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="orders")
    coffee_shop = relationship("CoffeeShop", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", lazy="selectin", cascade="all, delete-orphan", passive_deletes=True)


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_item_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_unit_price"),
        CheckConstraint("total_price >= 0", name="ck_order_item_total_price"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("menu_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("telegram_id", "coffee_shop_id", name="uq_favorite_user_shop"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coffee_shops.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="favorites")
    coffee_shop = relationship("CoffeeShop", back_populates="favorites")


@asynccontextmanager
async def get_session():
    async with session_maker() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)