## База данных

Проект использует PostgreSQL 13+. Схема совпадает с ORM-моделями бэкенда
(`backend/db/models.py`); интеграционные тесты создают БД именно из `schema.sql`,
поэтому расхождение сразу видно в CI.

### ER-диаграмма

```mermaid
erDiagram
    users ||--o{ coffee_shop_owners : "владеет"
    coffee_shops ||--o{ coffee_shop_owners : "принадлежит"
    users ||--o{ favorites : "сохраняет"
    coffee_shops ||--o{ favorites : "в избранном"
    coffee_shops ||--o{ menu_categories : "содержит"
    menu_categories ||--o{ menu_items : "группирует"
    coffee_shops ||--o{ menu_items : "продаёт"
    users ||--o{ orders : "оформляет"
    coffee_shops ||--o{ orders : "получает"
    orders ||--|{ order_items : "состоит из"
    menu_items ||--o{ order_items : "входит в"

    users {
        BIGINT telegram_id PK
        TEXT first_name
        TEXT last_name
        TEXT username
        TEXT language_code
        BOOLEAN is_premium
        VARCHAR phone
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
    coffee_shops {
        UUID id PK
        VARCHAR name
        TEXT description
        VARCHAR district
        TIME opening_time
        TIME closing_time
        TEXT address
        DECIMAL latitude
        DECIMAL longitude
        BOOLEAN is_active
        TEXT coffee_shop_image
        TIMESTAMPTZ created_at
    }
    coffee_shop_owners {
        UUID coffee_shop_id PK, FK
        BIGINT telegram_id PK, FK
    }
    menu_categories {
        UUID id PK
        UUID coffee_shop_id FK
        VARCHAR name
    }
    menu_items {
        UUID id PK
        UUID coffee_shop_id FK
        UUID category_id FK
        VARCHAR name
        TEXT description
        INTEGER base_price
        TEXT image_url
        BOOLEAN is_available
        TIMESTAMPTZ created_at
    }
    orders {
        UUID id PK
        BIGINT telegram_id FK
        UUID coffee_shop_id FK
        VARCHAR status
        INTEGER total_amount
        TIMESTAMPTZ pickup_time
        TIMESTAMPTZ created_at
    }
    order_items {
        UUID id PK
        UUID order_id FK
        UUID menu_item_id FK
        INTEGER quantity
        INTEGER unit_price
        INTEGER total_price
    }
    favorites {
        UUID id PK
        BIGINT telegram_id FK
        UUID coffee_shop_id FK
        TIMESTAMPTZ created_at
    }
```

### Таблицы

| Таблица | Назначение |
|---|---|
| `users` | Пользователи Telegram. Запись создаётся или обновляется при входе через Mini App (`POST /api/v1/auth/telegram`), пароль не хранится |
| `coffee_shops` | Кофейни. `district` нужен для поиска по району (US-01), `is_active = false` скрывает кофейню из каталога |
| `coffee_shop_owners` | Владельцы кофеен, связь многие-ко-многим. У кофейни может быть несколько владельцев |
| `menu_categories` | Категории меню кофейни, название уникально внутри кофейни |
| `menu_items` | Позиции меню. `is_available = false` — «Нет в наличии» (US-03, US-04) |
| `orders` | Заказы. Корзина — это заказ в статусе `cart` |
| `order_items` | Позиции заказа с ценой на момент оформления |
| `favorites` | Избранные кофейни, пара пользователь–кофейня уникальна |

### Статусы заказа

| Статус | Значение |
|---|---|
| `cart` | Корзина, заказ ещё не оформлен |
| `pending` | Оформлен, ждёт подтверждения кофейни |
| `confirmed` | Кофейня приняла заказ и готовит |
| `ready` | Готов, можно забирать |
| `completed` | Выдан |
| `cancelled` | Отменён |

Допустимые переходы описаны в `docs/api.md` и проверяются в `backend/services/orders.py`.

### Ограничения

- первичные и внешние ключи; обязательные поля (`NOT NULL`);
- `UNIQUE`: категория внутри кофейни, запись в избранном, позиция меню внутри заказа;
- частичный уникальный индекс `uq_order_cart_per_shop`: не больше одной корзины у пользователя в каждой кофейне;
- `CHECK`: цены и суммы не меньше нуля, количество больше нуля, статус заказа из списка;
- `ON DELETE CASCADE`: меню, владельцы и избранное удаляются вместе с кофейней, позиции — вместе с заказом.
  Заказы и позиции заказов от каскада защищены: кофейню или позицию меню из оформленного
  заказа удалить нельзя, API предлагает скрыть их флагом.

### SQL-скрипты

- `database/schema.sql` — создание структуры с нуля.
- `database/seed.sql` — тестовые данные (2 кофейни, меню, заказы, избранное).
- `database/migration_merge.sql` — приведение уже существующей БД к этой схеме: владельцы
  переносятся из старого столбца `owners` в `coffee_shop_owners`, статус `new` становится
  `pending`, добавляются поля профиля Telegram, район и время получения заказа.
  Скрипт можно запускать повторно.

```bash
createdb caffein
psql -d caffein -f database/schema.sql
psql -d caffein -f database/seed.sql
```
