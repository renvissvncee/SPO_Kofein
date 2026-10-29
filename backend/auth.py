from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db.models import CoffeeShop, CoffeeShopOwner, User, session_dependency
from .errors import (
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    error_responses,
)
from .security import (
    AuthenticationError,
    TelegramUser,
    create_access_token,
    decode_access_token,
    validate_telegram_init_data,
)

router = APIRouter(prefix="/auth", tags=["Аутентификация"])

# auto_error=False: отсутствие заголовка обрабатываем сами, чтобы вернуть 401
# в общем формате ошибок, а не 403 от FastAPI.
bearer_scheme = HTTPBearer(auto_error=False, description="JWT из POST /auth/telegram")


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(
        min_length=1,
        max_length=10_000,
        description="Строка Telegram.WebApp.initData без изменений",
    )


class DevAuthRequest(BaseModel):
    telegram_id: int = Field(gt=0, examples=[100001])
    first_name: str = Field(default="Dev user", min_length=1, max_length=100)
    username: str | None = Field(default=None, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool
    phone: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int = Field(description="Unix-время окончания действия токена")
    user: UserResponse


async def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """Возвращает telegram_id из проверенного JWT или отвечает 401."""
    if credentials is None:
        raise UnauthorizedError("Требуется аутентификация")
    if credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise UnauthorizedError("Invalid authorization header")
    try:
        return decode_access_token(credentials.credentials.strip(), get_settings())
    except (AuthenticationError, RuntimeError) as error:
        raise UnauthorizedError(str(error)) from error


async def require_coffee_shop_owner(
    shop_id: UUID,
    telegram_id: int = Depends(require_authenticated_user),
    session: AsyncSession = Depends(session_dependency),
) -> int:
    """Пропускает только владельца кофейни shop_id из пути запроса."""
    if await session.get(CoffeeShop, shop_id) is None:
        raise NotFoundError("Кофейня не найдена")
    result = await session.execute(
        select(CoffeeShopOwner).where(
            CoffeeShopOwner.coffee_shop_id == shop_id,
            CoffeeShopOwner.telegram_id == telegram_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise ForbiddenError("Действие доступно только владельцу кофейни")
    return telegram_id


async def upsert_telegram_user(
    telegram_user: TelegramUser,
    session: AsyncSession,
) -> User:
    values = {
        "telegram_id": telegram_user.id,
        "first_name": telegram_user.first_name,
        "last_name": telegram_user.last_name,
        "username": telegram_user.username,
        "language_code": telegram_user.language_code,
        "is_premium": telegram_user.is_premium,
    }
    statement = (
        insert(User)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_={
                **{key: value for key, value in values.items() if key != "telegram_id"},
                "updated_at": func.now(),
            },
        )
        .returning(User)
    )
    result = await session.execute(statement)
    user = result.scalar_one()
    await session.commit()
    return user


def _token_response(user: User) -> TokenResponse:
    access_token, expires_at = create_access_token(user.telegram_id, get_settings())
    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/telegram",
    response_model=TokenResponse,
    summary="Вход через Telegram Mini App",
    responses=error_responses(401, 422),
)
async def authenticate_with_telegram(
    data: TelegramAuthRequest,
    session: AsyncSession = Depends(session_dependency),
) -> TokenResponse:
    """Проверяет подпись initData и срок auth_date, создаёт или обновляет
    пользователя и выдаёт JWT."""
    try:
        telegram_user = validate_telegram_init_data(data.init_data, get_settings())
    except AuthenticationError as error:
        raise UnauthorizedError(str(error)) from error

    user = await upsert_telegram_user(telegram_user, session)
    return _token_response(user)


@router.post(
    "/dev",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Демонстрационный вход без Telegram",
    responses=error_responses(404, 422),
)
async def authenticate_for_development(
    data: DevAuthRequest,
    session: AsyncSession = Depends(session_dependency),
) -> TokenResponse:
    """Выдаёт JWT для указанного telegram_id без проверки Telegram.

    Работает только при DEV_AUTH_ENABLED=true, иначе отвечает 404, как будто
    эндпоинта нет. Нужен для Swagger, демонстрации и ручной проверки API.
    """
    if not get_settings().dev_auth_enabled:
        raise NotFoundError("Not Found")
    user = await upsert_telegram_user(
        TelegramUser(
            id=data.telegram_id,
            first_name=data.first_name,
            username=data.username,
        ),
        session,
    )
    return _token_response(user)
