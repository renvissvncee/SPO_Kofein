-- Схема БД проекта «Кофеин» (PostgreSQL 13+).
-- Соответствует ORM-моделям в backend/db/models.py.

-- Пользователь Telegram: создаётся или обновляется при входе через Mini App.
CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT,
    username TEXT,
    language_code TEXT,
    is_premium BOOLEAN NOT NULL DEFAULT FALSE,
    phone VARCHAR(30),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE coffee_shops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    district VARCHAR(100),
    opening_time TIME NOT NULL,
    closing_time TIME NOT NULL,
    address TEXT NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    coffee_shop_image TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE coffee_shop_owners (
    coffee_shop_id UUID REFERENCES coffee_shops(id) ON DELETE CASCADE,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    PRIMARY KEY (coffee_shop_id, telegram_id)
);

CREATE TABLE menu_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    CONSTRAINT uq_menu_category_shop_name UNIQUE (coffee_shop_id, name)
);

CREATE TABLE menu_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES menu_categories(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_price INTEGER NOT NULL,
    image_url TEXT,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_menu_item_base_price CHECK (base_price >= 0)
);

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    total_amount INTEGER NOT NULL DEFAULT 0,
    pickup_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_order_total_amount CHECK (total_amount >= 0),
    -- cart — корзина, pending — ждёт подтверждения, confirmed — готовится,
    -- ready — можно забирать, completed — выдан, cancelled — отменён.
    CONSTRAINT ck_order_status CHECK (status IN (
        'cart',
        'pending',
        'confirmed',
        'ready',
        'completed',
        'cancelled'
    ))
);

-- Не больше одной корзины у пользователя в каждой кофейне.
CREATE UNIQUE INDEX uq_order_cart_per_shop
    ON orders (telegram_id, coffee_shop_id)
    WHERE status = 'cart';

CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id UUID NOT NULL REFERENCES menu_items(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price INTEGER NOT NULL,
    total_price INTEGER NOT NULL,

    CONSTRAINT ck_order_item_quantity CHECK (quantity > 0),
    CONSTRAINT ck_order_item_unit_price CHECK (unit_price >= 0),
    CONSTRAINT ck_order_item_total_price CHECK (total_price >= 0),
    CONSTRAINT uq_order_item_menu_item UNIQUE (order_id, menu_item_id)
);

CREATE TABLE favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_favorite_user_shop UNIQUE (telegram_id, coffee_shop_id)
);
