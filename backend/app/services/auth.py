from datetime import datetime, timedelta, timezone

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import UnauthorizedError
from app.models.user import User

ALGORITHM = "HS256"

OAUTH_CONFIGS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": "openid email profile",
        "client_id_key": "GOOGLE_CLIENT_ID",
        "client_secret_key": "GOOGLE_CLIENT_SECRET",
        "redirect_uri_key": "GOOGLE_REDIRECT_URI",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": "read:user",
        "client_id_key": "GITHUB_CLIENT_ID",
        "client_secret_key": "GITHUB_CLIENT_SECRET",
        "redirect_uri_key": "GITHUB_REDIRECT_URI",
    },
}


def get_oauth_redirect_url(provider: str) -> str:
    cfg = OAUTH_CONFIGS[provider]
    client_id = getattr(settings, cfg["client_id_key"])
    redirect_uri = getattr(settings, cfg["redirect_uri_key"])

    if provider == "google":
        return (
            f"{cfg['auth_url']}?response_type=code"
            f"&client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={cfg['scopes']}"
            f"&access_type=offline"
        )
    # github
    return (
        f"{cfg['auth_url']}?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={cfg['scopes']}"
    )


async def exchange_code_for_user_info(provider: str, code: str) -> dict:
    cfg = OAUTH_CONFIGS[provider]
    client_id = getattr(settings, cfg["client_id_key"])
    client_secret = getattr(settings, cfg["client_secret_key"])
    redirect_uri = getattr(settings, cfg["redirect_uri_key"])

    async with httpx.AsyncClient() as client:
        # 토큰 교환
        token_resp = await client.post(
            cfg["token_url"],
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        # 유저 정보 조회
        user_resp = await client.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


def _extract_user_fields(provider: str, info: dict) -> dict:
    if provider == "google":
        return {
            "provider_id": info["sub"],
            "nickname": info.get("name") or info.get("email", "").split("@")[0],
            "avatar_url": info.get("picture"),
        }
    # github
    return {
        "provider_id": str(info["id"]),
        "nickname": info.get("login", ""),
        "avatar_url": info.get("avatar_url"),
    }


async def get_or_create_user(db: AsyncSession, provider: str, user_info: dict) -> User:
    fields = _extract_user_fields(provider, user_info)
    result = await db.execute(
        select(User).where(User.provider == provider, User.provider_id == fields["provider_id"])
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(provider=provider, **fields)
        db.add(user)
        await db.flush()
    else:
        user.nickname = fields["nickname"]
        user.avatar_url = fields["avatar_url"]
        user.updated_at = datetime.now(timezone.utc)

    return user


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "access"},
        settings.JWT_SECRET,
        algorithm=ALGORITHM,
    )


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh"},
        settings.JWT_SECRET,
        algorithm=ALGORITHM,
    )


def decode_token(token: str, expected_type: str = "access") -> int:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            raise UnauthorizedError("유효하지 않은 토큰 타입입니다.")
        return int(payload["sub"])
    except JWTError:
        raise UnauthorizedError("유효하지 않거나 만료된 토큰입니다.")
