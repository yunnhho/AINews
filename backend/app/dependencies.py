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


def _demo_admin() -> User:
    """데모 모드용 합성 관리자 — DB에 저장되지 않는 읽기전용 신원.

    Admin 엔드포인트는 이 객체의 필드를 사용하지 않고 인가 통과 표식으로만 쓴다.
    쓰기 요청은 DemoModeMiddleware가 전역 차단하므로 공개돼도 안전하다.
    """
    u = User()
    u.id = 0
    return u


async def get_admin_user(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(default=None, alias="access_token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    # 데모 모드: 인증 없이 Admin GET을 열어 준다(쓰기는 미들웨어가 차단).
    if settings.DEMO_MODE:
        return _demo_admin()
    user = await _get_user_from_token(authorization, access_cookie, db, required=True)
    assert user is not None
    if user.id not in settings.admin_user_ids_list:
        raise ForbiddenError()
    return user
