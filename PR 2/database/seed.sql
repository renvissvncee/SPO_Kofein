-- Пользователи
INSERT INTO users (telegram_id, first_name, phone)
VALUES
    (100001, 'Артем', '+79990000001'),
    (100002, 'Мария', '+79990000002'),
    (100003, 'Иван', '+79990000003');


-- Кофейни
INSERT INTO coffee_shops (
    id,
    name,
    description,
    opening_time,
    closing_time,
    address,
    latitude,
    longitude
)
VALUES
(
    '11111111-1111-1111-1111-111111111111',
    'Кофеин',
    'Кофейня с напитками и десертами',
    '08:00',
    '22:00',
    'ул. Ленина, 10',
    56.123456,
    47.123456
),
(
    '22222222-2222-2222-2222-222222222222',
    'Кофеин Центр',
    'Кофейня в центре города',
    '09:00',
    '23:00',
    'пр. Московский, 25',
    56.234567,
    47.234567
);


-- Владельцы кофеен
INSERT INTO coffee_shop_owners (coffee_shop_id, telegram_id)
VALUES
    ('11111111-1111-1111-1111-111111111111', 100001),
    ('22222222-2222-2222-2222-222222222222', 100002);


-- Категории меню
INSERT INTO menu_categories (id, coffee_shop_id, name)
VALUES
(
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    '11111111-1111-1111-1111-111111111111',
    'Кофе'
),
(
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    '11111111-1111-1111-1111-111111111111',
    'Десерты'
),
(
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
    '22222222-2222-2222-2222-222222222222',
    'Кофе'
);


-- Позиции меню
INSERT INTO menu_items (
    id,
    coffee_shop_id,
    category_id,
    name,
    description,
    base_price
)
VALUES
(
    'aaaaaaaa-1111-1111-1111-111111111111',
    '11111111-1111-1111-1111-111111111111',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'Капучино',
    'Классический капучино',
    250
),
(
    'bbbbbbbb-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'Латте',
    'Нежный латте',
    280
),
(
    'cccccccc-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    'Чизкейк',
    'Классический чизкейк',
    320
),
(
    'dddddddd-4444-4444-4444-444444444444',
    '22222222-2222-2222-2222-222222222222',
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
    'Американо',
    'Классический американо',
    180
);


-- Заказы
INSERT INTO orders (
    id,
    telegram_id,
    coffee_shop_id,
    status,
    total_amount
)
VALUES
(
    '99999999-9999-9999-9999-999999999999',
    100003,
    '11111111-1111-1111-1111-111111111111',
    'completed',
    530
),
(
    '88888888-8888-8888-8888-888888888888',
    100002,
    '22222222-2222-2222-2222-222222222222',
    'pending',
    360
);


-- Позиции заказов
INSERT INTO order_items (
    id,
    order_id,
    menu_item_id,
    quantity,
    unit_price,
    total_price
)
VALUES
(
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
    '99999999-9999-9999-9999-999999999999',
    'aaaaaaaa-1111-1111-1111-111111111111',
    1,
    250,
    250
),
(
    'ffffffff-ffff-ffff-ffff-ffffffffffff',
    '99999999-9999-9999-9999-999999999999',
    'cccccccc-3333-3333-3333-333333333333',
    1,
    280,
    280
),
(
    '77777777-7777-7777-7777-777777777777',
    '88888888-8888-8888-8888-888888888888',
    'dddddddd-4444-4444-4444-444444444444',
    2,
    180,
    360
);
