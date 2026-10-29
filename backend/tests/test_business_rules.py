"""Бизнес-правила без БД: переходы статусов заказа, часы работы, схемы запросов."""

from datetime import time
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.errors import ConflictError
from backend.schemas import CoffeeShopUpdate, OrderStatus, UserUpdate
from backend.services.coffee_shops import is_open_at
from backend.services.orders import CUSTOMER, OWNER, check_transition

S = OrderStatus


@pytest.mark.parametrize(
    ("current", "new", "actor"),
    [
        (S.pending, S.confirmed, OWNER),
        (S.pending, S.cancelled, CUSTOMER),
        (S.pending, S.cancelled, OWNER),
        (S.confirmed, S.ready, OWNER),
        (S.confirmed, S.cancelled, OWNER),
        (S.ready, S.completed, OWNER),
    ],
)
def test_allowed_transitions(current, new, actor) -> None:
    check_transition(current, new, actor)


@pytest.mark.parametrize(
    ("current", "new", "actor"),
    [
        (S.pending, S.confirmed, CUSTOMER),
        (S.confirmed, S.cancelled, CUSTOMER),
        (S.pending, S.completed, OWNER),
        (S.completed, S.cancelled, OWNER),
        (S.cancelled, S.pending, OWNER),
        (S.pending, S.cart, CUSTOMER),
    ],
)
def test_forbidden_transitions(current, new, actor) -> None:
    with pytest.raises(ConflictError):
        check_transition(current, new, actor)


def shop(opening: str, closing: str) -> SimpleNamespace:
    return SimpleNamespace(
        opening_time=time.fromisoformat(opening), closing_time=time.fromisoformat(closing)
    )


def test_opening_hours_same_day() -> None:
    assert is_open_at(shop("08:00", "22:00"), time(8, 0))
    assert not is_open_at(shop("08:00", "22:00"), time(22, 0))
    assert not is_open_at(shop("08:00", "22:00"), time(7, 59))


def test_opening_hours_past_midnight() -> None:
    assert is_open_at(shop("20:00", "04:00"), time(23, 0))
    assert is_open_at(shop("20:00", "04:00"), time(3, 0))
    assert not is_open_at(shop("20:00", "04:00"), time(12, 0))


def test_patch_rejects_null_for_required_field() -> None:
    with pytest.raises(ValidationError):
        CoffeeShopUpdate(name=None)
    assert CoffeeShopUpdate(description=None).model_fields_set == {"description"}


def test_phone_is_normalized() -> None:
    assert UserUpdate(phone="+7 (999) 000-00-01").phone == "+79990000001"
    with pytest.raises(ValidationError):
        UserUpdate(phone="89990000001")
