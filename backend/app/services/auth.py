import secrets
from datetime import UTC, datetime, timedelta

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import UnauthorizedError
from app.models.user import User

_AUTH_CODE_PREFIX = "auth_code:"
_AUTH_CODE_TTL = 300  # 5분 일회용

_OAUTH_STATE_PREFIX = "oauth_state:"
_OAUTH_STATE_TTL = 600  # 10분 — 로그인 왕복 동안만 유효

_REFRESH_JTI_PREFIX = "refresh_jti:"

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
    "kakao": {
        "auth_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url": "https://kauth.kakao.com/oauth/token",
        "userinfo_url": "https://kapi.kakao.com/v2/user/me",
        "scopes": "profile_nickname profile_image",
        "client_id_key": "KAKAO_CLIENT_ID",
        "client_secret_key": "KAKAO_CLIENT_SECRET",
        "redirect_uri_key": "KAKAO_REDIRECT_URI",
    },
}


async def create_oauth_state(platform: str) -> str:
    """CSRF 방어용 랜덤 state를 Redis에 저장한다. 값에 platform을 담아 콜백에서 복원한다."""
    from app.redis import get_redis
    redis = await get_redis()
    state = secrets.token_urlsafe(24)
    await redis.set(f"{_OAUTH_STATE_PREFIX}{state}", platform, ex=_OAUTH_STATE_TTL)
    return state


async def consume_oauth_state(state: str) -> str | None:
    """state를 원자적으로 조회·삭제하고 platform을 반환한다. 없으면 None(위조/만료/재사용)."""
    from app.redis import get_redis
    redis = await get_redis()
    return await redis.getdel(f"{_OAUTH_STATE_PREFIX}{state}")


def get_oauth_redirect_url(provider: str, state: str) -> str:
    """OAuth 인증 URL 생성. 호출부에서 발급한 랜덤 state를 그대로 전달한다(CSRF 방어)."""
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
            f"&state={state}"
        )
    if provider == "kakao":
        from urllib.parse import quote
        return (
            f"{cfg['auth_url']}?response_type=code"
            f"&client_id={client_id}"
            f"&redirect_uri={quote(redirect_uri, safe='')}"
            f"&scope={quote(cfg['scopes'], safe='')}"
            f"&state={state}"
        )
    # github
    return (
        f"{cfg['auth_url']}?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={cfg['scopes']}"
        f"&state={state}"
    )


async def create_auth_code(user_id: int) -> str:
    """일회용 인증 코드를 Redis에 저장하고 반환한다 (5분 TTL)."""
    from app.redis import get_redis
    redis = await get_redis()
    code = secrets.token_urlsafe(32)
    await redis.set(f"{_AUTH_CODE_PREFIX}{code}", str(user_id), ex=_AUTH_CODE_TTL)
    return code


async def consume_auth_code(code: str) -> int | None:
    """인증 코드를 원자적으로 조회·삭제하고 user_id를 반환한다. 없으면 None."""
    from app.redis import get_redis
    redis = await get_redis()
    user_id_str = await redis.getdel(f"{_AUTH_CODE_PREFIX}{code}")
    return int(user_id_str) if user_id_str else None


async def exchange_code_for_user_info(provider: str, code: str) -> dict:
    cfg = OAUTH_CONFIGS[provider]
    client_id = getattr(settings, cfg["client_id_key"])
    client_secret = getattr(settings, cfg["client_secret_key"])
    redirect_uri = getattr(settings, cfg["redirect_uri_key"])

    async with httpx.AsyncClient() as client:
        # 토큰 교환
        try:
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
        except httpx.HTTPError as exc:
            raise UnauthorizedError(f"{provider} 토큰 교환에 실패했습니다.") from exc

        # 일부 제공자(GitHub 등)는 실패 시에도 200에 error 필드를 담아 반환한다.
        access_token = token_data.get("access_token")
        if not access_token:
            err = token_data.get("error_description") or token_data.get("error") or "access_token 없음"
            raise UnauthorizedError(f"{provider} 인증 실패: {err}")

        # 유저 정보 조회
        try:
            user_resp = await client.get(
                cfg["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            user_resp.raise_for_status()
            return user_resp.json()
        except httpx.HTTPError as exc:
            raise UnauthorizedError(f"{provider} 사용자 정보 조회에 실패했습니다.") from exc


def _extract_user_fields(provider: str, info: dict) -> dict:
    if provider == "google":
        return {
            "provider_id": info["sub"],
            "nickname": info.get("name") or info.get("email", "").split("@")[0],
            "avatar_url": info.get("picture"),
        }
    if provider == "kakao":
        account = info.get("kakao_account", {})
        profile = account.get("profile", {})
        return {
            "provider_id": str(info["id"]),
            "nickname": profile.get("nickname") or f"user_{info['id']}",
            "avatar_url": profile.get("profile_image_url"),
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
        user.updated_at = datetime.now(UTC)

    return user


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "access"},
        settings.JWT_SECRET,
        algorithm=ALGORITHM,
    )


async def issue_refresh_token(user_id: int) -> str:
    """jti가 박힌 refresh token을 발급하고 Redis 화이트리스트에 등록한다(폐기·회전 가능)."""
    from app.redis import get_redis
    redis = await get_redis()
    jti = secrets.token_urlsafe(16)
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    token = jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh", "jti": jti},
        settings.JWT_SECRET,
        algorithm=ALGORITHM,
    )
    await redis.set(
        f"{_REFRESH_JTI_PREFIX}{jti}",
        str(user_id),
        ex=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    return token


def _decode_payload(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise UnauthorizedError("유효하지 않거나 만료된 토큰입니다.")
    if payload.get("type") != expected_type:
        raise UnauthorizedError("유효하지 않은 토큰 타입입니다.")
    return payload


def decode_token(token: str, expected_type: str = "access") -> int:
    return int(_decode_payload(token, expected_type)["sub"])


async def rotate_refresh_token(token: str) -> tuple[int, str]:
    """refresh token을 검증·일회용 소비하고 새 refresh token으로 회전한다.

    화이트리스트에 jti가 없으면(이미 회전/폐기됨 또는 재사용) 거부한다.
    """
    from app.redis import get_redis
    payload = _decode_payload(token, "refresh")
    jti = payload.get("jti")
    user_id = int(payload["sub"])
    redis = await get_redis()
    if not jti or not await redis.getdel(f"{_REFRESH_JTI_PREFIX}{jti}"):
        raise UnauthorizedError("유효하지 않거나 폐기된 리프레시 토큰입니다.")
    new_refresh = await issue_refresh_token(user_id)
    return user_id, new_refresh


async def revoke_refresh_token(token: str) -> None:
    """로그아웃 등에서 refresh token의 jti를 화이트리스트에서 제거한다(베스트에포트)."""
    from app.redis import get_redis
    try:
        payload = _decode_payload(token, "refresh")
    except UnauthorizedError:
        return
    jti = payload.get("jti")
    if jti:
        redis = await get_redis()
        await redis.delete(f"{_REFRESH_JTI_PREFIX}{jti}")
