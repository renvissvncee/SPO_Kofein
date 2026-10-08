-- Миграция существующей БД бэкенда (созданной через Base.metadata.create_all)
-- к объединённой схеме из schema.sql.
-- Данные не теряются: владельцы из coffee_shops.owners переносятся в coffee_shop_owners,
-- статус 'new' переименовывается в 'pending'.
-- Скрипт можно запускать повторно.

BEGIN;

-- users (telegram_id приходит из Telegram, автоинкремент не нужен)
ALTER TABLE users ALTER COLUMN telegram_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS users_telegram_id_seq;
ALTER TABLE users ALTER COLUMN phone TYPE VARCHAR(30);
ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ;
ALTER TABLE users ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE users ALTER COLUMN created_at SET DEFAULT NOW();

-- coffee_shops
ALTER TABLE coffee_shops ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE coffee_shops ALTER COLUMN name TYPE VARCHAR(255);
ALTER TABLE coffee_shops ADD COLUMN IF NOT EXISTS coffee_shop_image TEXT;
ALTER TABLE coffee_shops ALTER COLUMN is_active DROP NOT NULL;
ALTER TABLE coffee_shops ALTER COLUMN is_active SET DEFAULT TRUE;
ALTER TABLE coffee_shops ALTER COLUMN created_at TYPE TIMESTAMPTZ;
ALTER TABLE coffee_shops ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE coffee_shops ALTER COLUMN created_at SET DEFAULT NOW();

-- coffee_shop_owners: единственное место хранения владельцев.
-- Владельцы из старого столбца coffee_shops.owners переносятся в таблицу
-- (недостающие пользователи создаются), после чего столбец удаляется.
CREATE TABLE IF NOT EXISTS coffee_shop_owners (
    coffee_shop_id UUID REFERENCES coffee_shops(id) ON DELETE CASCADE,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    PRIMARY KEY (coffee_shop_id, telegram_id)
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'coffee_shops' AND column_name = 'owners'
    ) THEN
        INSERT INTO users (telegram_id)
        SELECT DISTINCT o.telegram_id
        FROM coffee_shops cs
        CROSS JOIN LATERAL unnest(cs.owners) AS o(telegram_id)
        WHERE o.telegram_id IS NOT NULL
        ON CONFLICT DO NOTHING;

        INSERT INTO coffee_shop_owners (coffee_shop_id, telegram_id)
        SELECT cs.id, o.telegram_id
        FROM coffee_shops cs
        CROSS JOIN LATERAL unnest(cs.owners) AS o(telegram_id)
        WHERE o.telegram_id IS NOT NULL
        ON CONFLICT DO NOTHING;

        ALTER TABLE coffee_shops DROP COLUMN owners;
    END IF;
END $$;

-- menu_categories
ALTER TABLE menu_categories ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE menu_categories ALTER COLUMN name TYPE VARCHAR(255);
ALTER TABLE menu_categories DROP CONSTRAINT IF EXISTS menu_categories_coffee_shop_id_fkey;
ALTER TABLE menu_categories ADD CONSTRAINT menu_categories_coffee_shop_id_fkey
    FOREIGN KEY (coffee_shop_id) REFERENCES coffee_shops(id) ON DELETE CASCADE;
ALTER TABLE menu_categories DROP CONSTRAINT IF EXISTS uq_menu_category_shop_name;
ALTER TABLE menu_categories ADD CONSTRAINT uq_menu_category_shop_name UNIQUE (coffee_shop_id, name);

-- menu_items
ALTER TABLE menu_items ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE menu_items ALTER COLUMN name TYPE VARCHAR(255);
ALTER TABLE menu_items ALTER COLUMN is_available DROP NOT NULL;
ALTER TABLE menu_items ALTER COLUMN is_available SET DEFAULT TRUE;
ALTER TABLE menu_items ALTER COLUMN created_at TYPE TIMESTAMPTZ;
ALTER TABLE menu_items ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE menu_items ALTER COLUMN created_at SET DEFAULT NOW();
ALTER TABLE menu_items DROP CONSTRAINT IF EXISTS menu_items_coffee_shop_id_fkey;
ALTER TABLE menu_items ADD CONSTRAINT menu_items_coffee_shop_id_fkey
    FOREIGN KEY (coffee_shop_id) REFERENCES coffee_shops(id) ON DELETE CASCADE;
ALTER TABLE menu_items DROP CONSTRAINT IF EXISTS menu_items_category_id_fkey;
ALTER TABLE menu_items ADD CONSTRAINT menu_items_category_id_fkey
    FOREIGN KEY (category_id) REFERENCES menu_categories(id) ON DELETE CASCADE;
ALTER TABLE menu_items DROP CONSTRAINT IF EXISTS ck_menu_item_base_price;
ALTER TABLE menu_items ADD CONSTRAINT ck_menu_item_base_price CHECK (base_price >= 0);

-- orders
ALTER TABLE orders ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_order_status;
UPDATE orders SET status = 'pending' WHERE status IS NULL OR status = 'new';
ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(30);
ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending';
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;
UPDATE orders SET total_amount = 0 WHERE total_amount IS NULL;
ALTER TABLE orders ALTER COLUMN total_amount SET DEFAULT 0;
ALTER TABLE orders ALTER COLUMN total_amount SET NOT NULL;
ALTER TABLE orders ALTER COLUMN created_at TYPE TIMESTAMPTZ;
ALTER TABLE orders ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE orders ALTER COLUMN created_at SET DEFAULT NOW();
ALTER TABLE orders DROP CONSTRAINT IF EXISTS ck_order_total_amount;
ALTER TABLE orders ADD CONSTRAINT ck_order_total_amount CHECK (total_amount >= 0);
ALTER TABLE orders ADD CONSTRAINT ck_order_status CHECK (status IN (
    'cart', 'pending', 'confirmed', 'ready', 'completed', 'cancelled'
));

-- order_items
ALTER TABLE order_items ALTER COLUMN id SET DEFAULT gen_random_uuid();
UPDATE order_items SET quantity = 1 WHERE quantity IS NULL;
ALTER TABLE order_items ALTER COLUMN quantity SET DEFAULT 1;
ALTER TABLE order_items ALTER COLUMN quantity SET NOT NULL;
ALTER TABLE order_items DROP CONSTRAINT IF EXISTS order_items_order_id_fkey;
ALTER TABLE order_items ADD CONSTRAINT order_items_order_id_fkey
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE;
ALTER TABLE order_items DROP CONSTRAINT IF EXISTS ck_order_item_quantity;
ALTER TABLE order_items ADD CONSTRAINT ck_order_item_quantity CHECK (quantity > 0);
ALTER TABLE order_items DROP CONSTRAINT IF EXISTS ck_order_item_unit_price;
ALTER TABLE order_items ADD CONSTRAINT ck_order_item_unit_price CHECK (unit_price >= 0);
ALTER TABLE order_items DROP CONSTRAINT IF EXISTS ck_order_item_total_price;
ALTER TABLE order_items ADD CONSTRAINT ck_order_item_total_price CHECK (total_price >= 0);

-- favorites
CREATE TABLE IF NOT EXISTS favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_favorite_user_shop UNIQUE (telegram_id, coffee_shop_id)
);
ALTER TABLE favorites ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE favorites ALTER COLUMN created_at TYPE TIMESTAMPTZ;
ALTER TABLE favorites ALTER COLUMN created_at DROP NOT NULL;
ALTER TABLE favorites ALTER COLUMN created_at SET DEFAULT NOW();
ALTER TABLE favorites DROP CONSTRAINT IF EXISTS favorites_telegram_id_fkey;
ALTER TABLE favorites ADD CONSTRAINT favorites_telegram_id_fkey
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE;
ALTER TABLE favorites DROP CONSTRAINT IF EXISTS favorites_coffee_shop_id_fkey;
ALTER TABLE favorites ADD CONSTRAINT favorites_coffee_shop_id_fkey
    FOREIGN KEY (coffee_shop_id) REFERENCES coffee_shops(id) ON DELETE CASCADE;

COMMIT;
