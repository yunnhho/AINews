"""웹 인증 쿠키 + CSRF(더블 서브밋) 헬퍼.

웹 플로우는 토큰을 URL/localStorage가 아닌 **HttpOnly 쿠키**로만 다룬다.
- access_token  : HttpOnly, 전체 경로(/), 짧은 수명
- refresh_token : HttpOnly, /v1/auth 경로 한정(노출 최소화), 긴 수명
- csrf_token    : JS에서 읽어 헤더로 되돌려보내는 더블 서브밋 토큰 (HttpOnly 아님)

운영에서 프론트(aipulse.kr)와 API(api.aipulse.kr)가 동일 사이트이므로 SameSite=lax가
교차 사이트 POST에 쿠키를 싣지 않아 1차 CSRF 방어가 되고, 더블 서브밋 토큰이 2차 방어다.
"""
import secrets

from starlette.responses import Response

from app.config import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"

_REFRESH_PATH = "/v1/auth"


def _common_kwargs() -> dict:
    return {
        "secure": settings.cookie_secure,
        "samesite": settings.COOKIE_SAMESITE,
        "domain": settings.cookie_domain,
    }


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> str:
    """access/refresh를 HttpOnly 쿠키로, CSRF 토큰을 읽기 가능 쿠키로 설정한다. CSRF 값을 반환."""
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        path="/",
        **_common_kwargs(),
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        path=_REFRESH_PATH,
        **_common_kwargs(),
    )
    csrf = secrets.token_urlsafe(32)
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=False,  # 프론트가 읽어 X-CSRF-Token 헤더로 되돌려보내야 함
        path="/",
        **_common_kwargs(),
    )
    return csrf


def clear_auth_cookies(response: Response) -> None:
    domain = settings.cookie_domain
    response.delete_cookie(ACCESS_COOKIE, path="/", domain=domain)
    response.delete_cookie(REFRESH_COOKIE, path=_REFRESH_PATH, domain=domain)
    response.delete_cookie(CSRF_COOKIE, path="/", domain=domain)
