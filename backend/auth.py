from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .config import get_settings
from .db.models import CoffeeShopOwner, User, session_dependency
from .security import (
    AuthenticationError,
    TelegramUser,
    create_access_token,
    decode_access_token,
    validate_telegram_init_data,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=10_000)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    user: UserResponse


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request.state.telegram_id = None
        request.state.authentication_error = None
        authorization = request.headers.get("Authorization")
        if authorization:
            scheme, separator, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not separator or not token.strip():
                request.state.authentication_error = "Invalid authorization header"
            else:
                try:
                    request.state.telegram_id = decode_access_token(
                        token.strip(), get_settings()
                    )
                except (AuthenticationError, RuntimeError) as error:
                    request.state.authentication_error = str(error)
        return await call_next(request)


def unauthorized(message: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_authenticated_user(request: Request) -> int:
    error = request.state.authentication_error
    if error:
        raise unauthorized(error)
    telegram_id = request.state.telegram_id
    if telegram_id is None:
        raise unauthorized()
    return telegram_id


async def require_coffee_shop_owner(
    coffee_shop_id: UUID,
    telegram_id: int = Depends(require_authenticated_user),
    session: AsyncSession = Depends(session_dependency),
) -> int:
    result = await session.execute(
        select(CoffeeShopOwner).where(
            CoffeeShopOwner.coffee_shop_id == coffee_shop_id,
            CoffeeShopOwner.telegram_id == telegram_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a coffee shop owner can perform this action",
        )
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


@router.post("/telegram", response_model=TokenResponse)
async def authenticate_with_telegram(
    data: TelegramAuthRequest,
    session: AsyncSession = Depends(session_dependency),
) -> TokenResponse:
    settings = get_settings()
    try:
        telegram_user = validate_telegram_init_data(data.init_data, settings)
    except AuthenticationError as error:
        raise unauthorized(str(error)) from error

    user = await upsert_telegram_user(telegram_user, session)
    access_token, expires_at = create_access_token(user.telegram_id, settings)
    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=UserResponse.model_validate(user),
    )
