# ☕ Кофеин

Агрегатор независимых кофеен города в виде Telegram Mini App. Гость находит кофейню и смотрит меню, покупатель собирает корзину и оформляет заказ к нужному времени, владелец ведёт страницу кофейни, меню и заказы.

[![CI](https://github.com/renvissvncee/SPO_Kofein/actions/workflows/ci.yml/badge.svg)](https://github.com/renvissvncee/SPO_Kofein/actions/workflows/ci.yml)

## Возможности

- Каталог кофеен: поиск по названию и району, фильтр «открыто в указанное время».
- Меню по категориям, позиции «Нет в наличии».
- Корзина отдельно для каждой кофейни, оформление заказа с временем получения.
- Статусы заказа: `pending → confirmed → ready → completed`, отмена покупателем или владельцем.
- Кабинет владельца: кофейни, совладельцы, категории и позиции меню, заказы.
- Избранные кофейни.

## Стек

| Слой | Технологии |
|---|---|
| Бэкенд | Python 3.11+, FastAPI, SQLAlchemy 2 (async), aiogram |
| Данные | PostgreSQL 16, Redis (выбранное время получения) |
| Клиент | React + Vite, Telegram Mini App |
| Вход | Telegram `initData` → JWT (HS256) |
| Качество | pytest, ruff, GitHub Actions |

## Быстрый старт

```bash
python3 -m venv backend/.venv && source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env            # впишите DATABASE_URL, JWT_SECRET, TELEGRAM_BOT_TOKEN

createdb caffein
psql -d caffein -f database/schema.sql
psql -d caffein -f database/seed.sql

uvicorn backend.main:app --reload
```

Swagger UI: <http://localhost:8000/docs>. Чтобы пробовать API без Telegram, включите `DEV_AUTH_ENABLED=true` и войдите через `POST /api/v1/auth/dev`.

## Тесты и линтер

```bash
cd backend
ruff check . && ruff format --check .
python -m pytest        # интеграционным тестам нужна БД из TEST_DATABASE_URL
```

## Документация

- [API-контракт](docs/api.md): 41 операция под `/api/v1`, роли, коды ошибок.
- [База данных](database/README.md): ER-диаграмма, таблицы, ограничения.
- [Бэкенд](backend/README.md): настройка, демо-вход, запуск Mini App через туннель.
- [Фронтенд](frontend/README.md)
- Продуктовые материалы: [docs/](docs/)

## Структура

```
backend/    FastAPI: api/ (маршруты по ролям), services/ (правила), db/ (модели)
database/   schema.sql, seed.sql, миграция, ER-диаграмма
frontend/   React-клиент
docs/       API-контракт и продуктовые документы
```
