# Kofein backend

## Setup

Run from the repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
```

Set a real `TELEGRAM_BOT_TOKEN`, a random `JWT_SECRET` of at least 32 characters,
and the PostgreSQL connection string in `.env`. Never commit the real `.env`.

For a new database, use `database/schema.sql` and then `database/seed.sql` if
sample data is needed. For an existing database, run `database/migration_merge.sql`.

`REDIS_URL` stores the selected order time; leave it empty to keep it in memory.

The API is served under `/api/v1`, see `docs/api.md` for the contract and
`http://localhost:8000/docs` for Swagger UI.

## Demo login without Telegram

Set `DEV_AUTH_ENABLED=true` in `.env` (local development only), then in Swagger call
`POST /api/v1/auth/dev` with `{"telegram_id": 100001}` (an owner from `seed.sql`),
copy `access_token` and press "Authorize". With the flag off the endpoint returns 404.

## Local Mini App with Cloudflare Quick Tunnel

Use three terminals from the repository root.

1. Start the API:

```bash
backend/.venv/bin/python -m uvicorn backend.main:app --reload
```

2. Expose it over HTTPS:

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the generated `https://...trycloudflare.com` URL into `.env`:

```env
MINI_APP_URL=https://...trycloudflare.com/mini-app/
```

Quick Tunnel generates a new hostname each time it starts. Update
`MINI_APP_URL` and restart the bot when the hostname changes.

3. Start the Telegram bot in polling mode:

```bash
backend/.venv/bin/python -m backend.bot
```

Send `/start` to the bot and press "Открыть Кофеин". The same Mini App is
also installed as the bot's menu button.

## Authentication flow

1. The bot opens the HTTPS Mini App URL.
2. Telegram injects the signed `Telegram.WebApp.initData` string into the page.
3. The page sends the unmodified value to `POST /api/v1/auth/telegram`.
4. The API validates Telegram's signature and `auth_date`, then creates or
   updates the user and returns a short-lived JWT.
5. The page keeps the JWT in `sessionStorage`. Its `window.kofeinApi.fetch`
   helper adds `Authorization: Bearer <token>` to protected API calls.

Coffee shop pages and menus are public. Everything under `/api/v1/me` always
derives the Telegram user ID from the JWT. Owner endpoints depend on
`require_coffee_shop_owner`; ownership is read from `coffee_shop_owners`.

## Tests and linter

```bash
cd backend
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python -m pytest
```

Unit tests need neither PostgreSQL nor a real bot token. Integration tests
(`tests/test_crud_api.py`) recreate the schema from `database/schema.sql` in the
database from `TEST_DATABASE_URL` (default
`postgresql+asyncpg://postgres:postgres@localhost:5432/kofein_test`) and are
skipped when it is unreachable. They drop the `public` schema, so tests ignore
`DATABASE_URL` and never touch the working database.

CI (`.github/workflows/ci.yml`) runs ruff and then pytest with PostgreSQL 16 on
every push and pull request.
