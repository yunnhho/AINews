from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.exceptions import ForbiddenError, UnauthorizedError
from app.models.user import User
from app.services.auth import decode_token


async def _get_user_from_token(
    authorization: str | None,
    db: AsyncSession,
    required: bool,
) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        if required:
            raise UnauthorizedError()
        return None

    token = authorization.removeprefix("Bearer ")
    user_id = decode_token(token, expected_type="access")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None and required:
        raise UnauthorizedError("존재하지 않는 사용자입니다.")
    return user


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _get_user_from_token(authorization, db, required=True)
    assert user is not None
    return user


async def optional_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    return await _get_user_from_token(authorization, db, required=False)


async def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if user.id not in settings.admin_user_ids_list:
        raise ForbiddenError()
    return user
