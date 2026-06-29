from fastapi import Cookie, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.exceptions import ForbiddenError, UnauthorizedError
from app.models.user import User
from app.services.auth import decode_token


def _extract_token(authorization: str | None, access_cookie: str | None) -> str | None:
    """Bearer 헤더(모바일) 또는 HttpOnly 쿠키(웹)에서 access token을 추출한다."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ")
    return access_cookie or None


async def _get_user_from_token(
    authorization: str | None,
    access_cookie: str | None,
    db: AsyncSession,
    required: bool,
) -> User | None:
    token = _extract_token(authorization, access_cookie)
    if not token:
        if required:
            raise UnauthorizedError()
        return None

    # 선택 인증(게스트 허용) 경로에서 만료·위조 토큰은 401이 아니라 게스트로 처리한다.
    # (그렇지 않으면 토큰 만료 시 피드 등 공개 엔드포인트 전체가 401로 깨진다.)
    try:
        user_id = decode_token(token, expected_type="access")
    except UnauthorizedError:
        if required:
            raise
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None and required:
        raise UnauthorizedError("존재하지 않는 사용자입니다.")
    return user


async def get_current_user(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(default=None, alias="access_token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _get_user_from_token(authorization, access_cookie, db, required=True)
    assert user is not None
    return user


async def optional_user(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(default=None, alias="access_token"),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    return await _get_user_from_token(authorization, access_cookie, db, required=False)


async def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if user.id not in settings.admin_user_ids_list:
        raise ForbiddenError()
    return user
