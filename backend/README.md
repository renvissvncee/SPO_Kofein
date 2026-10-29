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

For an existing database, run `PR 2/database/migrations/001_telegram_auth.sql`.
For a new database, use `PR 2/database/schema.sql` and then `seed.sql` if sample
data is needed.

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
3. The page sends the unmodified value to `POST /auth/telegram`.
4. The API validates Telegram's signature and `auth_date`, then creates or
   updates the user and returns a short-lived JWT.
5. The page keeps the JWT in `sessionStorage`. Its `window.kofeinApi.fetch`
   helper adds `Authorization: Bearer <token>` to protected API calls.

`/coffee_shops` and `/menu` are public. Cart and favorites are protected and
always derive the Telegram user ID from the JWT. Owner-only endpoints should
depend on `require_coffee_shop_owner`; ownership is read from
`coffee_shop_owners`.

## Tests

```bash
cd backend
.venv/bin/python -m pytest
```

The authentication and authorization tests do not require PostgreSQL or a real
Telegram bot token.
