import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import NullPool

from ..config import get_settings


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
_ORDER_STATUSES_SQL = ", ".join(f"'{status}'" for status in ORDER_STATUSES)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    """Пользователь Telegram. Создаётся или обновляется при входе через Mini App."""

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str | None] = mapped_column(Text)
    username: Mapped[str | None] = mapped_column(Text)
    language_code: Mapped[str | None] = mapped_column(Text)
    is_premium: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("FALSE")
    )
    phone: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    ownerships: Mapped[list["CoffeeShopOwner"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class CoffeeShop(Base):
    __tablename__ = "coffee_shops"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(String(100))
    opening_time: Mapped[time] = mapped_column(Time, nullable=False)
    closing_time: Mapped[time] = mapped_column(Time, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(DECIMAL(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(DECIMAL(9, 6), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )
    coffee_shop_image: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()

    categories: Mapped[list["MenuCategory"]] = relationship(
        back_populates="coffee_shop", cascade="all, delete-orphan", passive_deletes=True
    )
    menu_items: Mapped[list["MenuItem"]] = relationship(
        back_populates="coffee_shop", cascade="all, delete-orphan", passive_deletes=True
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="coffee_shop")
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="coffee_shop", cascade="all, delete-orphan", passive_deletes=True
    )
    ownerships: Mapped[list["CoffeeShopOwner"]] = relationship(
        back_populates="coffee_shop",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    @property
    def owners(self) -> list[int]:
        """telegram_id владельцев (из таблицы coffee_shop_owners)."""
        return [ownership.telegram_id for ownership in self.ownerships]


class CoffeeShopOwner(Base):
    """Связь многие-ко-многим пользователей и кофеен (владельцы)."""

    __tablename__ = "coffee_shop_owners"

    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coffee_shops.id", ondelete="CASCADE"),
        primary_key=True,
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )

    coffee_shop: Mapped[CoffeeShop] = relationship(back_populates="ownerships")
    user: Mapped[User] = relationship(back_populates="ownerships")


class MenuCategory(Base):
    __tablename__ = "menu_categories"
    __table_args__ = (
        UniqueConstraint("coffee_shop_id", "name", name="uq_menu_category_shop_name"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coffee_shops.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    coffee_shop: Mapped[CoffeeShop] = relationship(back_populates="categories")
    menu_items: Mapped[list["MenuItem"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MenuItem.name",
    )


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (CheckConstraint("base_price >= 0", name="ck_menu_item_base_price"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coffee_shops.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("menu_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_price: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )
    created_at: Mapped[datetime] = _created_at()

    coffee_shop: Mapped[CoffeeShop] = relationship(back_populates="menu_items")
    category: Mapped[MenuCategory] = relationship(back_populates="menu_items")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="menu_item")


class Order(Base):
    """Заказ. Корзина — это заказ в статусе cart (одна на пользователя и кофейню)."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_order_total_amount"),
        CheckConstraint(f"status IN ({_ORDER_STATUSES_SQL})", name="ck_order_status"),
        Index(
            "uq_order_cart_per_shop",
            "telegram_id",
            "coffee_shop_id",
            unique=True,
            postgresql_where=text("status = 'cart'"),
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False
    )
    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coffee_shops.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default=text("'pending'")
    )
    total_amount: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    pickup_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()

    user: Mapped[User] = relationship(back_populates="orders")
    coffee_shop: Mapped[CoffeeShop] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_item_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_unit_price"),
        CheckConstraint("total_price >= 0", name="ck_order_item_total_price"),
        UniqueConstraint("order_id", "menu_item_id", name="uq_order_item_menu_item"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    menu_item: Mapped[MenuItem] = relationship(back_populates="order_items", lazy="selectin")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("telegram_id", "coffee_shop_id", name="uq_favorite_user_shop"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False
    )
    coffee_shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coffee_shops.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = _created_at()

    user: Mapped[User] = relationship(back_populates="favorites")
    coffee_shop: Mapped[CoffeeShop] = relationship(back_populates="favorites")


settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=False,
    # В тестах каждый запрос идёт в своём цикле событий, общий пул там мешает.
    **({"poolclass": NullPool} if settings.database_null_pool else {}),
)
session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session


async def session_dependency() -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
