# API-контракт «Кофеин»

Один бэкенд обслуживает два клиента, оба работают с общей БД только через этот API:

- **приложение покупателя** (Telegram Mini App, `frontend/`) — поиск кофеен, меню, корзина, заказы;
- **приложение кофейни** (будет позже, пока Swagger) — управление кофейней, меню и заказами.

Живая документация с возможностью отправить запрос: `http://localhost:8000/docs` (Swagger UI),
машиночитаемая схема: `http://localhost:8000/openapi.json`. Эндпоинты в Swagger сгруппированы так же,
как разделы этого документа.

**Содержание**

1. [Общие правила](#1-общие-правила): адрес, формат, аутентификация, ошибки, коды ответов
2. [Аутентификация](#2-аутентификация)
3. [Публичная часть: кофейни и меню](#3-публичная-часть-кофейни-и-меню) — без токена
4. [Покупатель](#4-покупатель) — профиль, время заказа, избранное, корзина, заказы
5. [Владелец кофейни](#5-владелец-кофейни) — кофейни, совладельцы, меню, заказы кофейни
6. [Статусы заказа](#6-статусы-заказа)
7. [Сводная таблица CRUD](#7-сводная-таблица-crud)

---

## 1. Общие правила

### Адрес и формат

- Префикс всех путей: **`/api/v1`**. В таблицах ниже он опущен. Исключение — служебный `GET /health`.
- Тела запросов и ответов — `application/json`, кодировка UTF-8.
- Идентификаторы кофеен, категорий, позиций и заказов — UUID; пользователя — `telegram_id` (целое число).
- Время работы — `HH:MM` или `HH:MM:SS`; дата и время — ISO 8601 **с часовым поясом**
  (`2026-11-01T09:30:00+03:00`). Деньги — целые рубли.
- `PATCH` — частичное обновление: меняются только переданные поля. Обязательное поле нельзя
  обнулить (`{"name": null}` → 422), необязательное можно (`{"description": null}`).

### Аутентификация

Вход выполняется через Telegram (раздел 2). Сервер выдаёт JWT, который передаётся в заголовке:

```
Authorization: Bearer <access_token>
```

- Подпись HMAC-SHA256 (`alg: HS256`), секрет из переменной окружения `JWT_SECRET` (не короче 32 символов).
- Срок жизни — `JWT_TTL_SECONDS`, по умолчанию 3600 секунд. Клиент получает его в поле `expires_at`.
- В токене: `sub` = `telegram_id`, `iat`, `exp`, `iss = kofein-api`, `aud = kofein-mini-app`.
- Пользователь всегда определяется **по токену**: `telegram_id` в запросах покупателя не передаётся,
  чужие корзины и заказы получить нельзя.

### Роли

| Роль | Кто это | Как проверяется |
|---|---|---|
| Гость | Любой клиент | Токен не нужен |
| Покупатель | Пользователь, вошедший через Telegram | Действующий JWT, иначе 401 |
| Владелец | Пользователь из `coffee_shop_owners` для этой кофейни | JWT + запись в `coffee_shop_owners`, иначе 403 |

### Формат ошибки

Любая ошибка, включая 401, 404 неизвестного пути и ошибки валидации, имеет один вид:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Некорректные данные запроса",
    "details": [
      { "field": "body.name", "message": "String should have at least 1 character" }
    ]
  }
}
```

`details` есть только там, где он полезен: у ошибок валидации и у `ITEM_UNAVAILABLE` при оформлении заказа.

### Коды ответов

| Код | Когда | `error.code` |
|---|---|---|
| 200 | Успешное чтение или изменение | — |
| 201 | Запись создана | — |
| 204 | Удаление, тела ответа нет | — |
| 401 | Нет заголовка `Authorization`, токен испорчен, подписан другим ключом или истёк; неверная подпись Telegram | `UNAUTHORIZED` |
| 403 | Пользователь не владелец кофейни | `FORBIDDEN` |
| 404 | Записи нет или она чужая (чужой заказ выглядит как несуществующий) | `NOT_FOUND` |
| 409 | Запрос корректен, но нарушает бизнес-правило или уникальность | см. ниже |
| 422 | Тело или параметры не прошли валидацию | `VALIDATION_ERROR` |

Коды 409:

| `error.code` | Причина |
|---|---|
| `DUPLICATE_CATEGORY` | Категория с таким названием в кофейне уже есть |
| `CATEGORY_NOT_EMPTY` | Удаление категории, в которой есть позиции |
| `ITEM_IN_ORDERS` | Удаление позиции меню, которая есть в оформленных заказах (её можно скрыть `is_available=false`) |
| `SHOP_HAS_ORDERS` | Удаление кофейни, у которой есть оформленные заказы (её можно скрыть `is_active=false`) |
| `LAST_OWNER` | Удаление последнего владельца кофейни |
| `ITEM_UNAVAILABLE` | Позиции нет в наличии: при добавлении в корзину или оформлении заказа |
| `QUANTITY_LIMIT` | Больше 50 штук одной позиции |
| `EMPTY_CART` | Оформление заказа из пустой корзины |
| `PICKUP_TIME_PASSED`, `SHOP_CLOSED` | Время получения в прошлом или вне часов работы кофейни |
| `INVALID_STATUS_TRANSITION` | Переход статуса заказа не разрешён (раздел 6) |
| `CONFLICT` | Прочее нарушение ограничений БД |

---

## 2. Аутентификация

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| POST | `/auth/telegram` | Вход из Mini App: проверяет подпись `initData` и возраст `auth_date`, создаёт или обновляет пользователя, выдаёт JWT | 200, 401, 422 |
| POST | `/auth/dev` | Демонстрационный вход без Telegram по `telegram_id`. Работает только при `DEV_AUTH_ENABLED=true`, иначе 404 | 200, 404, 422 |

Регистрации по логину и паролю нет: пользователь — это аккаунт Telegram, его личность подтверждает
подпись Telegram (HMAC-SHA256 от токена бота). Первый вход и есть регистрация.

Запрос `POST /auth/telegram`:

```json
{ "init_data": "query_id=AAH...&user=%7B%22id%22%3A100001...&auth_date=1793277745&hash=5f3c..." }
```

Запрос `POST /auth/dev` (только для разработки и Swagger):

```json
{ "telegram_id": 100001, "first_name": "Артём", "username": "owner_kofein" }
```

Ответ обоих:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_at": 1793281345,
  "user": {
    "telegram_id": 100001,
    "first_name": "Артём",
    "last_name": null,
    "username": "owner_kofein",
    "language_code": "ru",
    "is_premium": false,
    "phone": null,
    "created_at": "2026-10-29T12:42:25.719010Z"
  }
}
```

---

## 3. Публичная часть: кофейни и меню

Доступна без токена. Скрытые кофейни (`is_active=false`) здесь не видны.

| Метод | Путь | Что делает | User story |
|---|---|---|---|
| GET | `/coffee-shops` | Список кофеен. Фильтры: `q` — поиск по названию, адресу и району; `district` — район; `open_at=HH:MM` — открытые в это время | US-01 |
| GET | `/coffee-shops/{shop_id}` | Страница кофейни: название, описание, адрес, район, часы работы | US-02 |
| GET | `/coffee-shops/{shop_id}/menu` | Меню по категориям. Недоступные позиции возвращаются с `is_available=false` | US-03 |
| GET | `/coffee-shops/{shop_id}/menu/items/{item_id}` | Одна позиция меню | US-03 |

Кофейня:

```json
{
  "id": "56fd5205-beb0-41e9-a682-63ca8886bb92",
  "name": "Кофеин",
  "description": "Кофейня с напитками и десертами",
  "district": "Ленинский",
  "opening_time": "08:00:00",
  "closing_time": "22:00:00",
  "address": "ул. Ленина, 10",
  "latitude": 56.123456,
  "longitude": 47.123456,
  "is_active": true,
  "coffee_shop_image": null
}
```

Меню:

```json
[
  {
    "id": "87291bf5-48b4-488a-8f0a-47e6471a2165",
    "name": "Кофе",
    "items": [
      {
        "id": "50043321-157c-4149-af0f-c34a4e3340d1",
        "category_id": "87291bf5-48b4-488a-8f0a-47e6471a2165",
        "name": "Капучино",
        "description": null,
        "base_price": 250,
        "image_url": null,
        "is_available": true
      }
    ]
  }
]
```

---

## 4. Покупатель

Все пути требуют JWT. Пользователь берётся из токена.

### 4.1. Профиль

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| GET | `/me` | Мой профиль | 200 |
| PATCH | `/me` | Изменить телефон: `{"phone": "+7 (999) 000-00-01"}` → хранится как `+79990000001`; `null` удаляет | 200, 422 |

Создание профиля — это вход через Telegram, а имя и username обновляются при каждом входе.
Удаление аккаунта не предусмотрено: история заказов должна сохраняться для кофейни.

### 4.2. Время заказа

Желаемое время получения, выбранное до оформления. Хранится в Redis (ключ `tg:{telegram_id}`, сутки).

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| GET | `/me/order-time` | Выбранное время | 200, 404 |
| PUT | `/me/order-time` | Выбрать или изменить: `{"order_time": "2026-11-01T09:30:00+03:00"}`, не в прошлом | 200, 422 |
| DELETE | `/me/order-time` | Сбросить | 204, 404 |

Ответ: `{"order_time": "2026-11-01T09:30:00+03:00", "updated_at": "2026-10-29T12:42:26Z"}`.
Чтобы показать кофейни, открытые в это время, клиент вызывает `GET /coffee-shops?open_at=09:30`.

### 4.3. Избранное

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| GET | `/me/favorites` | Избранные кофейни: `{"coffee_shops": [ ...кофейни... ]}` | 200 |
| PUT | `/me/favorites/{shop_id}` | Добавить. Идемпотентно: 201 при добавлении, 200 если уже была | 201, 200, 404 |
| DELETE | `/me/favorites/{shop_id}` | Убрать | 204, 404 |

### 4.4. Корзина

Корзина — заказ в статусе `cart`, одна на каждую кофейню. Позиция в корзине адресуется по
`menu_item_id`. Когда из корзины убрана последняя позиция, корзина удаляется.
Цена позиции в корзине следует за ценой в меню.

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| GET | `/me/carts` | Все мои корзины | 200 |
| GET | `/me/carts/{shop_id}` | Корзина в кофейне | 200, 404 |
| POST | `/me/carts/{shop_id}/items` | Добавить: `{"menu_item_id": "...", "quantity": 2}` (1–50). Если позиция уже есть, количество увеличивается | 201, 200, 404, 409 |
| PATCH | `/me/carts/{shop_id}/items/{menu_item_id}` | Задать количество: `{"quantity": 3}` | 200, 404, 422 |
| DELETE | `/me/carts/{shop_id}/items/{menu_item_id}` | Убрать позицию | 204, 404 |
| DELETE | `/me/carts/{shop_id}` | Очистить корзину | 204, 404 |

Корзина:

```json
{
  "id": "971de679-5aca-4310-ac4b-9b9bf365a0e2",
  "coffee_shop_id": "56fd5205-beb0-41e9-a682-63ca8886bb92",
  "total_amount": 500,
  "items": [
    {
      "id": "179356e2-da20-469c-a5b3-5ad6f7fb3e9e",
      "menu_item_id": "50043321-157c-4149-af0f-c34a4e3340d1",
      "quantity": 2,
      "unit_price": 250,
      "total_price": 500,
      "menu_item": { "id": "50043321-...", "name": "Капучино", "base_price": 250, "is_available": true }
    }
  ]
}
```

### 4.5. Заказы

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| POST | `/me/orders` | Оформить заказ из корзины: `{"coffee_shop_id": "...", "pickup_time": "..."}`. `pickup_time` необязателен, по умолчанию берётся из `/me/order-time` | 201, 404, 409 |
| GET | `/me/orders` | История заказов, новые сверху. Фильтр `?status=pending` | 200 |
| GET | `/me/orders/{order_id}` | Один заказ | 200, 404 |
| PATCH | `/me/orders/{order_id}` | Отменить: `{"status": "cancelled"}`, только из `pending` | 200, 404, 409 |

При оформлении сервер проверяет, что корзина не пуста, кофейня активна, все позиции в наличии,
а время получения не в прошлом и попадает в часы работы. Цены фиксируются на момент оформления.

Заказ — это корзина с дополнительными полями:

```json
{
  "id": "971de679-5aca-4310-ac4b-9b9bf365a0e2",
  "coffee_shop_id": "56fd5205-beb0-41e9-a682-63ca8886bb92",
  "telegram_id": 100003,
  "status": "pending",
  "total_amount": 500,
  "pickup_time": "2026-11-02T09:00:00Z",
  "created_at": "2026-10-29T12:42:26.019949Z",
  "items": [ ... ]
}
```

---

## 5. Владелец кофейни

Все пути требуют JWT. Пути с `{shop_id}` доступны только владельцам этой кофейни: не владелец получает 403,
несуществующая кофейня — 404.

### 5.1. Кофейни

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| GET | `/me/coffee-shops` | Мои кофейни, включая скрытые | 200 |
| POST | `/coffee-shops` | Создать кофейню. Любой вошедший пользователь, он становится первым владельцем | 201, 422 |
| GET | `/coffee-shops/{shop_id}/manage` | Кофейня для владельца, в том числе скрытая, со списком `owners` | 200, 403, 404 |
| PATCH | `/coffee-shops/{shop_id}` | Изменить описание, адрес, район, часы работы, обложку, `is_active` | 200, 403, 404, 409, 422 |
| DELETE | `/coffee-shops/{shop_id}` | Удалить вместе с меню, избранным и корзинами. Если есть оформленные заказы — 409 `SHOP_HAS_ORDERS` | 204, 403, 404, 409 |

Тело `POST /coffee-shops` (в `PATCH` те же поля, все необязательные):

```json
{
  "name": "Кофеин",
  "description": "Кофейня с напитками и десертами",
  "district": "Ленинский",
  "opening_time": "08:00",
  "closing_time": "22:00",
  "address": "ул. Ленина, 10",
  "latitude": 56.123456,
  "longitude": 47.123456,
  "is_active": true,
  "coffee_shop_image": null
}
```

`closing_time` может быть меньше `opening_time`: это кофейня, работающая через полночь.

### 5.2. Совладельцы

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| GET | `/coffee-shops/{shop_id}/owners` | Владельцы кофейни | 200, 403 |
| POST | `/coffee-shops/{shop_id}/owners` | Добавить: `{"telegram_id": 100002}`. Пользователь должен хотя бы раз войти в Mini App | 201, 403, 404 |
| DELETE | `/coffee-shops/{shop_id}/owners/{telegram_id}` | Удалить владельца. Последнего удалить нельзя | 204, 403, 404, 409 |

### 5.3. Меню

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| POST | `/coffee-shops/{shop_id}/menu/categories` | Добавить категорию: `{"name": "Кофе"}` | 201, 403, 409 |
| PATCH | `/coffee-shops/{shop_id}/menu/categories/{category_id}` | Переименовать | 200, 403, 404, 409 |
| DELETE | `/coffee-shops/{shop_id}/menu/categories/{category_id}` | Удалить пустую категорию | 204, 403, 404, 409 |
| POST | `/coffee-shops/{shop_id}/menu/items` | Добавить позицию | 201, 403, 404, 422 |
| PATCH | `/coffee-shops/{shop_id}/menu/items/{item_id}` | Изменить цену, наличие, категорию, описание | 200, 403, 404, 422 |
| DELETE | `/coffee-shops/{shop_id}/menu/items/{item_id}` | Удалить. Убирается и из корзин. Если есть в оформленных заказах — 409 | 204, 403, 404, 409 |

Чтение меню — публичное (раздел 3). Тело `POST .../menu/items`:

```json
{
  "category_id": "87291bf5-48b4-488a-8f0a-47e6471a2165",
  "name": "Капучино",
  "description": "Классический капучино",
  "base_price": 250,
  "image_url": null,
  "is_available": true
}
```

«Скрыть позицию» из US-04 — это `PATCH` с `{"is_available": false}`: покупатель видит
«Нет в наличии» и не может добавить позицию в корзину.

### 5.4. Заказы кофейни

| Метод | Путь | Что делает | Ответ |
|---|---|---|---|
| GET | `/coffee-shops/{shop_id}/orders` | Заказы кофейни, новые сверху. Фильтр `?status=pending` | 200, 403 |
| GET | `/coffee-shops/{shop_id}/orders/{order_id}` | Один заказ | 200, 403, 404 |
| PATCH | `/coffee-shops/{shop_id}/orders/{order_id}` | Сменить статус: `{"status": "confirmed"}` | 200, 403, 404, 409, 422 |

---

## 6. Статусы заказа

```
cart ──POST /me/orders──▶ pending ──▶ confirmed ──▶ ready ──▶ completed
                             │            │
                             └──▶ cancelled ◀──┘
```

| Из | В | Кто | Через |
|---|---|---|---|
| `cart` | `pending` | Покупатель | `POST /me/orders` |
| `pending` | `confirmed` | Владелец | `PATCH /coffee-shops/{shop_id}/orders/{order_id}` |
| `pending` | `cancelled` | Покупатель или владелец | `PATCH /me/orders/{order_id}` или `PATCH /coffee-shops/{shop_id}/orders/{order_id}` |
| `confirmed` | `ready` | Владелец | `PATCH /coffee-shops/{shop_id}/orders/{order_id}` |
| `confirmed` | `cancelled` | Владелец | `PATCH /coffee-shops/{shop_id}/orders/{order_id}` |
| `ready` | `completed` | Владелец | `PATCH /coffee-shops/{shop_id}/orders/{order_id}` |

Любой другой переход — 409 `INVALID_STATUS_TRANSITION`. Неизвестный статус — 422.

---

## 7. Сводная таблица CRUD

| Сущность | Create | Read | Update | Delete |
|---|---|---|---|---|
| Пользователь | вход через Telegram | `GET /me` | `PATCH /me` | не предусмотрено |
| Кофейня | `POST /coffee-shops` | `GET /coffee-shops`, `GET /coffee-shops/{id}` | `PATCH /coffee-shops/{id}` | `DELETE /coffee-shops/{id}` |
| Владелец кофейни | `POST .../owners` | `GET .../owners` | — (связь без полей) | `DELETE .../owners/{telegram_id}` |
| Категория меню | `POST .../menu/categories` | `GET .../menu` | `PATCH .../menu/categories/{id}` | `DELETE .../menu/categories/{id}` |
| Позиция меню | `POST .../menu/items` | `GET .../menu/items/{id}` | `PATCH .../menu/items/{id}` | `DELETE .../menu/items/{id}` |
| Время заказа | `PUT /me/order-time` | `GET /me/order-time` | `PUT /me/order-time` | `DELETE /me/order-time` |
| Избранное | `PUT /me/favorites/{shop_id}` | `GET /me/favorites` | — (связь без полей) | `DELETE /me/favorites/{shop_id}` |
| Корзина и её позиции | `POST /me/carts/{shop_id}/items` | `GET /me/carts`, `GET /me/carts/{shop_id}` | `PATCH .../items/{menu_item_id}` | `DELETE .../items/{menu_item_id}`, `DELETE /me/carts/{shop_id}` |
| Заказ | `POST /me/orders` | `GET /me/orders[/{id}]`, `GET .../orders[/{id}]` кофейни | `PATCH` статуса | не удаляется: отменяется статусом `cancelled` |

### Что изменилось относительно старых эндпоинтов

| Было | Стало |
|---|---|
| `GET /coffee_shops` | `GET /coffee-shops` |
| `GET /menu?id=...` | `GET /coffee-shops/{shop_id}/menu` |
| `POST /set_order_time` с `action` | `GET` / `PUT` / `DELETE /me/order-time` |
| `GET`, `POST`, `DELETE /favorites` с `tg_id` | `GET /me/favorites`, `PUT` / `DELETE /me/favorites/{shop_id}` |
| `GET`, `POST`, `DELETE /cart` с `tg_id`, `quantity: -1` | `/me/carts/...`, количество меняется через `PATCH` |
| `POST /auth/telegram` | `POST /api/v1/auth/telegram` |
