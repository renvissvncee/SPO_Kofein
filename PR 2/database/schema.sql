CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    phone VARCHAR(30),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE coffee_shops (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    opening_time TIME NOT NULL,
    closing_time TIME NOT NULL,
    address TEXT NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE coffee_shop_owners (
    coffee_shop_id UUID REFERENCES coffee_shops(id) ON DELETE CASCADE,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    PRIMARY KEY (coffee_shop_id, telegram_id)
);

CREATE TABLE menu_categories (
    id UUID PRIMARY KEY,
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    UNIQUE (coffee_shop_id, name)
);

CREATE TABLE menu_items (
    id UUID PRIMARY KEY,
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES menu_categories(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_price INTEGER NOT NULL CHECK (base_price >= 0),
    image_url TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE orders (
    id UUID PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    total_amount INTEGER NOT NULL CHECK (total_amount >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CHECK (status IN (
        'pending',
        'confirmed',
        'completed',
        'cancelled'
    ))
);

CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id UUID NOT NULL REFERENCES menu_items(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
    total_price INTEGER NOT NULL CHECK (total_price >= 0)
);