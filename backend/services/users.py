from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User
from ..errors import UnauthorizedError
from ..schemas import UserUpdate


async def get(session: AsyncSession, telegram_id: int) -> User:
    user = await session.get(User, telegram_id)
    if user is None:
        # Токен валиден, но пользователя уже нет в БД: нужно войти заново
        raise UnauthorizedError("Пользователь не найден, войдите заново")
    return user


async def update(session: AsyncSession, telegram_id: int, data: UserUpdate) -> User:
    user = await get(session, telegram_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user
