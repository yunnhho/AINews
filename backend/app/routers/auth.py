from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundError, UnauthorizedError
from app.models.user import User
from app.schemas.auth import AuthCodeExchangeRequest, TokenResponse, UserProfile
from app.services import auth as auth_svc

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── 카카오 ──────────────────────────────────────────────────────────────────

@router.get("/kakao")
async def kakao_redirect(platform: str = Query("web")):
    return RedirectResponse(url=auth_svc.get_oauth_redirect_url("kakao", platform=platform))


@router.get("/kakao/callback")
async def kakao_callback(
    code: str = Query(...),
    state: str = Query("web"),
    db: AsyncSession = Depends(get_db),
):
    user_info = await auth_svc.exchange_code_for_user_info("kakao", code)
    user = await auth_svc.get_or_create_user(db, "kakao", user_info)

    if state == "mobile":
        auth_code = await auth_svc.create_auth_code(user.id)
        return RedirectResponse(url=f"aipulse://auth/callback?code={auth_code}", status_code=302)

    # 웹 플로우 — JWT를 웹 프론트엔드로 전달
    access_token = auth_svc.create_access_token(user.id)
    params = urlencode({
        "access_token": access_token,
        "user_id": user.id,
        "nickname": user.nickname or "",
        "avatar_url": user.avatar_url or "",
    })
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?{params}", status_code=302)


# ── /me — /{provider} 앞에 등록해야 섀도잉되지 않음 ────────────────────────

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Google / GitHub ─────────────────────────────────────────────────────────

@router.get("/{provider}")
async def oauth_redirect(provider: str, platform: str = Query("web")):
    if provider not in ("google", "github"):
        raise NotFoundError("provider")
    return RedirectResponse(url=auth_svc.get_oauth_redirect_url(provider, platform=platform))


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query("web"),
    db: AsyncSession = Depends(get_db),
):
    if provider not in ("google", "github"):
        raise NotFoundError("provider")

    user_info = await auth_svc.exchange_code_for_user_info(provider, code)
    user = await auth_svc.get_or_create_user(db, provider, user_info)

    if state == "mobile":
        auth_code = await auth_svc.create_auth_code(user.id)
        return RedirectResponse(url=f"aipulse://auth/callback?code={auth_code}", status_code=302)

    # 웹 플로우
    access_token = auth_svc.create_access_token(user.id)
    params = urlencode({
        "access_token": access_token,
        "user_id": user.id,
        "nickname": user.nickname or "",
        "avatar_url": user.avatar_url or "",
    })
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?{params}", status_code=302)


# ── 일회용 코드 교환 ────────────────────────────────────────────────────────

@router.post("/exchange", response_model=TokenResponse)
async def exchange_auth_code(
    request: AuthCodeExchangeRequest,
    db: AsyncSession = Depends(get_db),
):
    """모바일 딥링크에서 받은 일회용 코드를 JWT로 교환한다."""
    user_id = await auth_svc.consume_auth_code(request.code)
    if user_id is None:
        raise UnauthorizedError("유효하지 않거나 만료된 인증 코드입니다.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError()

    return TokenResponse(
        access_token=auth_svc.create_access_token(user.id),
        refresh_token=auth_svc.create_refresh_token(user.id),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── 기타 ────────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    user_id = auth_svc.decode_token(body.refresh_token, expected_type="refresh")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError()

    return TokenResponse(
        access_token=auth_svc.create_access_token(user.id),
        refresh_token=auth_svc.create_refresh_token(user.id),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.delete("/logout", status_code=204)
async def logout():
    # JWT는 stateless — 클라이언트에서 토큰 삭제
    return None
