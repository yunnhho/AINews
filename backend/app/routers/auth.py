from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.config import settings
from app.cookies import set_auth_cookies, clear_auth_cookies
from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundError, UnauthorizedError
from app.models.user import User
from app.schemas.auth import (
    AuthCodeExchangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserProfile,
)
from app.services import auth as auth_svc

router = APIRouter(prefix="/v1/auth", tags=["auth"])


async def _resolve_user_or_404(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("존재하지 않는 사용자입니다.")
    return user


async def _complete_login(platform: str, user: User) -> Response:
    """플랫폼별 로그인 마무리.

    - mobile: 일회용 코드를 딥링크로 전달(토큰은 /exchange에서 교환)
    - web   : access/refresh를 HttpOnly 쿠키로 설정하고 프론트로 리다이렉트(토큰 URL 노출 없음)
    """
    if platform == "mobile":
        auth_code = await auth_svc.create_auth_code(user.id)
        return RedirectResponse(url=f"aipulse://auth/callback?code={auth_code}", status_code=302)

    access_token = auth_svc.create_access_token(user.id)
    refresh_token = await auth_svc.issue_refresh_token(user.id)
    resp = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback", status_code=302)
    set_auth_cookies(resp, access_token, refresh_token)
    return resp


# ── 카카오 ──────────────────────────────────────────────────────────────────

@router.get("/kakao")
async def kakao_redirect(platform: str = Query("web")):
    state = await auth_svc.create_oauth_state(platform)
    return RedirectResponse(url=auth_svc.get_oauth_redirect_url("kakao", state))


@router.get("/kakao/callback")
async def kakao_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    platform = await auth_svc.consume_oauth_state(state)
    if platform is None:
        raise UnauthorizedError("유효하지 않거나 만료된 인증 요청입니다.")
    user_info = await auth_svc.exchange_code_for_user_info("kakao", code)
    user = await auth_svc.get_or_create_user(db, "kakao", user_info)
    await db.commit()
    return await _complete_login(platform, user)


# ── /me — /{provider} 앞에 등록해야 섀도잉되지 않음 ────────────────────────

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Google / GitHub ─────────────────────────────────────────────────────────

@router.get("/{provider}")
async def oauth_redirect(provider: str, platform: str = Query("web")):
    if provider not in ("google", "github"):
        raise NotFoundError("provider")
    state = await auth_svc.create_oauth_state(platform)
    return RedirectResponse(url=auth_svc.get_oauth_redirect_url(provider, state))


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    if provider not in ("google", "github"):
        raise NotFoundError("provider")

    platform = await auth_svc.consume_oauth_state(state)
    if platform is None:
        raise UnauthorizedError("유효하지 않거나 만료된 인증 요청입니다.")
    user_info = await auth_svc.exchange_code_for_user_info(provider, code)
    user = await auth_svc.get_or_create_user(db, provider, user_info)
    await db.commit()
    return await _complete_login(platform, user)


# ── 일회용 코드 교환 (모바일) ────────────────────────────────────────────────

@router.post("/exchange", response_model=TokenResponse)
async def exchange_auth_code(
    request: AuthCodeExchangeRequest,
    db: AsyncSession = Depends(get_db),
):
    """모바일 딥링크에서 받은 일회용 코드를 JWT로 교환한다."""
    user_id = await auth_svc.consume_auth_code(request.code)
    if user_id is None:
        raise UnauthorizedError("유효하지 않거나 만료된 인증 코드입니다.")

    user = await _resolve_user_or_404(db, user_id)
    return TokenResponse(
        access_token=auth_svc.create_access_token(user.id),
        refresh_token=await auth_svc.issue_refresh_token(user.id),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── 토큰 갱신 (회전) ──────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token(
    body: RefreshTokenRequest | None = None,
    refresh_cookie: str | None = Cookie(default=None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
):
    """refresh token을 회전한다. 웹은 쿠키, 모바일은 본문으로 받는다."""
    body_token = body.refresh_token if body and body.refresh_token else None
    token = body_token or refresh_cookie
    if not token:
        raise UnauthorizedError("리프레시 토큰이 없습니다.")

    user_id, new_refresh = await auth_svc.rotate_refresh_token(token)
    user = await _resolve_user_or_404(db, user_id)
    access_token = auth_svc.create_access_token(user.id)

    # 웹(쿠키) 플로우 — 토큰을 본문에 노출하지 않고 쿠키만 갱신.
    if refresh_cookie and not body_token:
        resp = Response(status_code=204)
        set_auth_cookies(resp, access_token, new_refresh)
        return resp

    # 모바일 — JSON 반환.
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── 로그아웃 ──────────────────────────────────────────────────────────────────

@router.delete("/logout", status_code=204)
async def logout(
    body: RefreshTokenRequest | None = None,
    refresh_cookie: str | None = Cookie(default=None, alias="refresh_token"),
):
    """refresh token을 폐기하고 인증 쿠키를 제거한다."""
    token = (body.refresh_token if body and body.refresh_token else None) or refresh_cookie
    if token:
        await auth_svc.revoke_refresh_token(token)
    resp = Response(status_code=204)
    clear_auth_cookies(resp)
    return resp
