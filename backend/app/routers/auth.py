from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundError, UnauthorizedError
from app.models.user import User
from app.schemas.auth import TokenResponse, UserProfile
from app.services import auth as auth_svc

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.get("/{provider}")
async def oauth_redirect(provider: str):
    if provider not in ("google", "github"):
        raise NotFoundError("provider")
    return RedirectResponse(url=auth_svc.get_oauth_redirect_url(provider))


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    from urllib.parse import urlencode

    user_info = await auth_svc.exchange_code_for_user_info(provider, code)
    user = await auth_svc.get_or_create_user(db, provider, user_info)

    access_token = auth_svc.create_access_token(user.id)
    params = urlencode({
        "access_token": access_token,
        "user_id": user.id,
        "nickname": user.nickname or "",
        "avatar_url": user.avatar_url or "",
    })
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?{params}",
        status_code=302,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    user_id = auth_svc.decode_token(refresh_token, expected_type="refresh")
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


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
