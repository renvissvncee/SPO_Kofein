"""Интеграционные тесты CRUD на реальном PostgreSQL.

Каждый тест получает чистую БД, созданную из database/schema.sql.
Без доступного PostgreSQL тесты пропускаются (в CI база поднимается).
"""

from datetime import UTC, datetime, timedelta

import pytest

API = "/api/v1"
OWNER_ID = 100001
CUSTOMER_ID = 100003

SHOP = {
    "name": "Кофеин",
    "description": "Кофейня с напитками и десертами",
    "district": "Ленинский",
    "opening_time": "00:00",
    "closing_time": "23:59",
    "address": "ул. Ленина, 10",
    "latitude": 56.123456,
    "longitude": 47.123456,
}


@pytest.fixture
def owner(login):
    return login(OWNER_ID, "Артём")


@pytest.fixture
def customer(login):
    return login(CUSTOMER_ID, "Никита")


@pytest.fixture
def shop(client, owner):
    response = client.post(f"{API}/coffee-shops", json=SHOP, headers=owner)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def menu_item(client, owner, shop):
    """Категория «Кофе» и позиция «Капучино» за 250 ₽."""
    category = client.post(
        f"{API}/coffee-shops/{shop['id']}/menu/categories", json={"name": "Кофе"}, headers=owner
    ).json()
    response = client.post(
        f"{API}/coffee-shops/{shop['id']}/menu/items",
        json={"category_id": category["id"], "name": "Капучино", "base_price": 250},
        headers=owner,
    )
    assert response.status_code == 201, response.text
    return response.json()


def future() -> str:
    """Завтра в 12:00 UTC: в будущем и внутри часов работы тестовой кофейни."""
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    return tomorrow.replace(hour=12, minute=0, second=0, microsecond=0).isoformat()


# ---------- Кофейни ----------


def test_coffee_shop_full_crud(client, owner, shop):
    shop_id = shop["id"]
    assert shop["owners"] == [OWNER_ID]

    listed = client.get(f"{API}/coffee-shops").json()
    assert [item["id"] for item in listed] == [shop_id]
    assert client.get(f"{API}/coffee-shops/{shop_id}").json()["name"] == "Кофеин"

    updated = client.patch(
        f"{API}/coffee-shops/{shop_id}",
        json={"opening_time": "09:00", "description": "Новые часы"},
        headers=owner,
    )
    assert updated.status_code == 200
    assert updated.json()["opening_time"] == "09:00:00"
    assert client.get(f"{API}/coffee-shops/{shop_id}").json()["opening_time"] == "09:00:00"

    assert client.delete(f"{API}/coffee-shops/{shop_id}", headers=owner).status_code == 204
    assert client.get(f"{API}/coffee-shops/{shop_id}").status_code == 404


def test_coffee_shop_search_by_name_district_and_time(client, owner):
    day = {**SHOP, "opening_time": "08:00", "closing_time": "22:00"}
    night = {
        **SHOP,
        "name": "Сова",
        "district": "Центральный",
        "opening_time": "20:00",
        "closing_time": "04:00",
    }
    client.post(f"{API}/coffee-shops", json=day, headers=owner)
    client.post(f"{API}/coffee-shops", json=night, headers=owner)

    def names(query: str) -> list[str]:
        return [shop["name"] for shop in client.get(f"{API}/coffee-shops?{query}").json()]

    assert names("q=сов") == ["Сова"]
    assert names("district=центральный") == ["Сова"]
    assert names("open_at=02:00") == ["Сова"]
    assert names("open_at=21:00") == ["Кофеин", "Сова"]
    assert names("q=нет-такой") == []


def test_hidden_coffee_shop_is_visible_only_to_owner(client, owner, shop):
    client.patch(f"{API}/coffee-shops/{shop['id']}", json={"is_active": False}, headers=owner)

    assert client.get(f"{API}/coffee-shops").json() == []
    assert client.get(f"{API}/coffee-shops/{shop['id']}").status_code == 404
    mine = client.get(f"{API}/me/coffee-shops", headers=owner).json()
    assert mine[0]["is_active"] is False


def test_coffee_shop_validation_and_null_fields(client, owner, shop):
    bad = client.post(f"{API}/coffee-shops", json={**SHOP, "name": "  "}, headers=owner)
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"

    null_name = client.patch(f"{API}/coffee-shops/{shop['id']}", json={"name": None}, headers=owner)
    assert null_name.status_code == 422


def test_only_owner_can_change_coffee_shop(client, customer, shop):
    response = client.patch(
        f"{API}/coffee-shops/{shop['id']}", json={"name": "Захват"}, headers=customer
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert client.delete(f"{API}/coffee-shops/{shop['id']}", headers=customer).status_code == 403


def test_owner_of_other_shop_is_forbidden(client, login, shop):
    other_owner = login(100002, "Ильгиз")
    client.post(f"{API}/coffee-shops", json={**SHOP, "name": "Чужая"}, headers=other_owner)

    response = client.post(
        f"{API}/coffee-shops/{shop['id']}/menu/categories",
        json={"name": "Чай"},
        headers=other_owner,
    )
    assert response.status_code == 403


def test_coffee_shop_with_orders_cannot_be_deleted(client, owner, customer, shop, menu_item):
    client.post(
        f"{API}/me/carts/{shop['id']}/items",
        json={"menu_item_id": menu_item["id"]},
        headers=customer,
    )
    client.post(f"{API}/me/orders", json={"coffee_shop_id": shop["id"]}, headers=customer)

    response = client.delete(f"{API}/coffee-shops/{shop['id']}", headers=owner)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SHOP_HAS_ORDERS"


# ---------- Владельцы ----------


def test_co_owners_crud(client, owner, login, shop):
    second = login(100002, "Ильгиз")
    owners_url = f"{API}/coffee-shops/{shop['id']}/owners"

    added = client.post(owners_url, json={"telegram_id": 100002}, headers=owner)
    assert added.status_code == 201
    assert {user["telegram_id"] for user in client.get(owners_url, headers=second).json()} == {
        OWNER_ID,
        100002,
    }

    assert client.delete(f"{owners_url}/{OWNER_ID}", headers=second).status_code == 204
    last = client.delete(f"{owners_url}/100002", headers=second)
    assert last.status_code == 409
    assert last.json()["error"]["code"] == "LAST_OWNER"


def test_unknown_user_cannot_become_owner(client, owner, shop):
    response = client.post(
        f"{API}/coffee-shops/{shop['id']}/owners", json={"telegram_id": 999}, headers=owner
    )
    assert response.status_code == 404


# ---------- Меню ----------


def test_menu_category_crud(client, owner, shop):
    base = f"{API}/coffee-shops/{shop['id']}/menu/categories"
    category = client.post(base, json={"name": "Кофе"}, headers=owner)
    assert category.status_code == 201
    category_id = category.json()["id"]

    duplicate = client.post(base, json={"name": "Кофе"}, headers=owner)
    assert duplicate.status_code == 409

    renamed = client.patch(f"{base}/{category_id}", json={"name": "Кофе и чай"}, headers=owner)
    assert renamed.json()["name"] == "Кофе и чай"

    menu = client.get(f"{API}/coffee-shops/{shop['id']}/menu").json()
    assert [category["name"] for category in menu] == ["Кофе и чай"]

    assert client.delete(f"{base}/{category_id}", headers=owner).status_code == 204
    assert client.get(f"{API}/coffee-shops/{shop['id']}/menu").json() == []


def test_non_empty_category_cannot_be_deleted(client, owner, shop, menu_item):
    response = client.delete(
        f"{API}/coffee-shops/{shop['id']}/menu/categories/{menu_item['category_id']}", headers=owner
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CATEGORY_NOT_EMPTY"


def test_menu_item_crud_and_availability(client, owner, shop, menu_item):
    item_url = f"{API}/coffee-shops/{shop['id']}/menu/items/{menu_item['id']}"
    assert client.get(item_url).json()["base_price"] == 250

    updated = client.patch(item_url, json={"base_price": 270, "is_available": False}, headers=owner)
    assert updated.status_code == 200
    menu = client.get(f"{API}/coffee-shops/{shop['id']}/menu").json()
    assert menu[0]["items"][0]["is_available"] is False
    assert menu[0]["items"][0]["base_price"] == 270

    assert client.delete(item_url, headers=owner).status_code == 204
    assert client.get(item_url).status_code == 404


def test_menu_item_validation(client, owner, shop, menu_item):
    items_url = f"{API}/coffee-shops/{shop['id']}/menu/items"
    negative = client.post(
        items_url,
        json={"category_id": menu_item["category_id"], "name": "Латте", "base_price": -1},
        headers=owner,
    )
    assert negative.status_code == 422

    foreign_category = client.post(
        items_url,
        json={"category_id": shop["id"], "name": "Латте", "base_price": 100},
        headers=owner,
    )
    assert foreign_category.status_code == 404


# ---------- Профиль и время заказа ----------


def test_profile_read_and_update(client, customer):
    profile = client.get(f"{API}/me", headers=customer).json()
    assert profile["telegram_id"] == CUSTOMER_ID
    assert profile["first_name"] == "Никита"

    updated = client.patch(f"{API}/me", json={"phone": "+7 (999) 000-00-03"}, headers=customer)
    assert updated.json()["phone"] == "+79990000003"
    assert client.patch(f"{API}/me", json={"phone": "123"}, headers=customer).status_code == 422


def test_order_time_crud(client, customer):
    url = f"{API}/me/order-time"
    assert client.get(url, headers=customer).status_code == 404

    when = future()
    assert client.put(url, json={"order_time": when}, headers=customer).status_code == 200
    stored = client.get(url, headers=customer).json()
    assert datetime.fromisoformat(stored["order_time"]) == datetime.fromisoformat(when)

    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    assert client.put(url, json={"order_time": past}, headers=customer).status_code == 422

    assert client.delete(url, headers=customer).status_code == 204
    assert client.get(url, headers=customer).status_code == 404


# ---------- Избранное ----------


def test_favorites_crud_is_idempotent(client, customer, shop):
    url = f"{API}/me/favorites/{shop['id']}"
    assert client.put(url, headers=customer).status_code == 201
    assert client.put(url, headers=customer).status_code == 200

    favorites = client.get(f"{API}/me/favorites", headers=customer).json()
    assert [item["id"] for item in favorites["coffee_shops"]] == [shop["id"]]

    assert client.delete(url, headers=customer).status_code == 204
    assert client.delete(url, headers=customer).status_code == 404


# ---------- Корзина ----------


def test_cart_crud(client, customer, shop, menu_item):
    cart_url = f"{API}/me/carts/{shop['id']}"
    item_url = f"{cart_url}/items/{menu_item['id']}"
    assert client.get(cart_url, headers=customer).status_code == 404

    added = client.post(
        f"{cart_url}/items", json={"menu_item_id": menu_item["id"], "quantity": 2}, headers=customer
    )
    assert added.status_code == 201
    assert added.json()["total_amount"] == 500

    again = client.post(
        f"{cart_url}/items", json={"menu_item_id": menu_item["id"]}, headers=customer
    )
    assert again.status_code == 200
    assert again.json()["items"][0]["quantity"] == 3

    changed = client.patch(item_url, json={"quantity": 1}, headers=customer)
    assert changed.json()["total_amount"] == 250
    assert len(client.get(f"{API}/me/carts", headers=customer).json()) == 1

    assert client.delete(item_url, headers=customer).status_code == 204
    assert client.get(cart_url, headers=customer).status_code == 404


def test_cart_is_private_and_cleared(client, login, customer, shop, menu_item):
    client.post(
        f"{API}/me/carts/{shop['id']}/items",
        json={"menu_item_id": menu_item["id"]},
        headers=customer,
    )
    stranger = login(100009, "Чужой")
    assert client.get(f"{API}/me/carts/{shop['id']}", headers=stranger).status_code == 404

    assert client.delete(f"{API}/me/carts/{shop['id']}", headers=customer).status_code == 204
    assert client.get(f"{API}/me/carts", headers=customer).json() == []


def test_unavailable_item_cannot_be_added(client, owner, customer, shop, menu_item):
    client.patch(
        f"{API}/coffee-shops/{shop['id']}/menu/items/{menu_item['id']}",
        json={"is_available": False},
        headers=owner,
    )
    response = client.post(
        f"{API}/me/carts/{shop['id']}/items",
        json={"menu_item_id": menu_item["id"]},
        headers=customer,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ITEM_UNAVAILABLE"


def test_price_change_updates_open_cart(client, owner, customer, shop, menu_item):
    client.post(
        f"{API}/me/carts/{shop['id']}/items",
        json={"menu_item_id": menu_item["id"]},
        headers=customer,
    )
    client.patch(
        f"{API}/coffee-shops/{shop['id']}/menu/items/{menu_item['id']}",
        json={"base_price": 300},
        headers=owner,
    )
    cart = client.get(f"{API}/me/carts/{shop['id']}", headers=customer).json()
    assert cart["total_amount"] == 300


# ---------- Заказы ----------


def place_order(client, customer, shop, menu_item, **extra):
    client.post(
        f"{API}/me/carts/{shop['id']}/items",
        json={"menu_item_id": menu_item["id"], "quantity": 2},
        headers=customer,
    )
    return client.post(
        f"{API}/me/orders", json={"coffee_shop_id": shop["id"], **extra}, headers=customer
    )


def test_order_lifecycle(client, owner, customer, shop, menu_item):
    created = place_order(client, customer, shop, menu_item)
    assert created.status_code == 201
    order = created.json()
    assert order["status"] == "pending"
    assert order["total_amount"] == 500
    assert client.get(f"{API}/me/carts", headers=customer).json() == []

    shop_orders = f"{API}/coffee-shops/{shop['id']}/orders"
    assert [item["id"] for item in client.get(shop_orders, headers=owner).json()] == [order["id"]]

    for new_status in ("confirmed", "ready", "completed"):
        response = client.patch(
            f"{shop_orders}/{order['id']}", json={"status": new_status}, headers=owner
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == new_status

    history = client.get(f"{API}/me/orders?status=completed", headers=customer).json()
    assert [item["id"] for item in history] == [order["id"]]


def test_customer_can_cancel_only_pending_order(client, owner, customer, shop, menu_item):
    order = place_order(client, customer, shop, menu_item).json()
    my_order = f"{API}/me/orders/{order['id']}"

    cancelled = client.patch(my_order, json={"status": "cancelled"}, headers=customer)
    assert cancelled.json()["status"] == "cancelled"

    second = place_order(client, customer, shop, menu_item).json()
    client.patch(
        f"{API}/coffee-shops/{shop['id']}/orders/{second['id']}",
        json={"status": "confirmed"},
        headers=owner,
    )
    late = client.patch(
        f"{API}/me/orders/{second['id']}", json={"status": "cancelled"}, headers=customer
    )
    assert late.status_code == 409
    assert late.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_customer_cannot_confirm_own_order(client, customer, shop, menu_item):
    order = place_order(client, customer, shop, menu_item).json()
    response = client.patch(
        f"{API}/me/orders/{order['id']}", json={"status": "confirmed"}, headers=customer
    )
    assert response.status_code == 409


def test_invalid_status_value_is_rejected(client, owner, customer, shop, menu_item):
    order = place_order(client, customer, shop, menu_item).json()
    response = client.patch(
        f"{API}/coffee-shops/{shop['id']}/orders/{order['id']}",
        json={"status": "delivered"},
        headers=owner,
    )
    assert response.status_code == 422


def test_empty_cart_cannot_be_ordered(client, customer, shop):
    response = client.post(
        f"{API}/me/orders", json={"coffee_shop_id": shop["id"]}, headers=customer
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMPTY_CART"


def test_order_uses_selected_pickup_time(client, customer, shop, menu_item):
    when = future()
    client.put(f"{API}/me/order-time", json={"order_time": when}, headers=customer)

    order = place_order(client, customer, shop, menu_item).json()
    assert datetime.fromisoformat(order["pickup_time"]) == datetime.fromisoformat(when)
    assert client.get(f"{API}/me/order-time", headers=customer).status_code == 404


def test_order_outside_opening_hours_is_rejected(client, owner, customer, shop, menu_item):
    client.patch(
        f"{API}/coffee-shops/{shop['id']}",
        json={"opening_time": "08:00", "closing_time": "09:00"},
        headers=owner,
    )
    tomorrow_noon = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    response = place_order(client, customer, shop, menu_item, pickup_time=tomorrow_noon.isoformat())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SHOP_CLOSED"


def test_orders_are_private(client, login, customer, shop, menu_item):
    order = place_order(client, customer, shop, menu_item).json()
    stranger = login(100009, "Чужой")
    assert client.get(f"{API}/me/orders/{order['id']}", headers=stranger).status_code == 404
    assert (
        client.get(f"{API}/coffee-shops/{shop['id']}/orders", headers=stranger).status_code == 403
    )


def test_ordered_menu_item_cannot_be_deleted(client, owner, customer, shop, menu_item):
    place_order(client, customer, shop, menu_item)
    response = client.delete(
        f"{API}/coffee-shops/{shop['id']}/menu/items/{menu_item['id']}", headers=owner
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ITEM_IN_ORDERS"
