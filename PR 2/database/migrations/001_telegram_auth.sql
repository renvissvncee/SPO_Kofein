BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS language_code TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE users SET first_name = 'Telegram user' WHERE first_name IS NULL;
ALTER TABLE users ALTER COLUMN first_name SET NOT NULL;

ALTER TABLE coffee_shops ADD COLUMN IF NOT EXISTS coffee_shop_image TEXT;

CREATE TABLE IF NOT EXISTS coffee_shop_owners (
    coffee_shop_id UUID REFERENCES coffee_shops(id) ON DELETE CASCADE,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    PRIMARY KEY (coffee_shop_id, telegram_id)
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'coffee_shops' AND column_name = 'owners'
    ) THEN
        EXECUTE '
            INSERT INTO coffee_shop_owners (coffee_shop_id, telegram_id)
            SELECT shop.id, owner.telegram_id
            FROM coffee_shops AS shop
            CROSS JOIN LATERAL unnest(shop.owners) AS owner(telegram_id)
            JOIN users ON users.telegram_id = owner.telegram_id
            ON CONFLICT DO NOTHING
        ';

        ALTER TABLE coffee_shops DROP COLUMN owners;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS favorites (
    id UUID PRIMARY KEY,
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    coffee_shop_id UUID NOT NULL REFERENCES coffee_shops(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (telegram_id, coffee_shop_id)
);

ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check;
UPDATE orders SET status = 'pending' WHERE status = 'new';
ALTER TABLE orders ADD CONSTRAINT orders_status_check CHECK (
    status IN ('cart', 'pending', 'confirmed', 'completed', 'cancelled')
);

COMMIT;
