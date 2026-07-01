"""기본 보안 미들웨어 — 보안 헤더 + IP 기반 레이트리밋 + CSRF(더블 서브밋).

운영 환경(APP_ENV=production)에서만 HSTS를 켜고, 레이트리밋은 Redis 장애 시
요청을 막지 않도록(fail-open) 설계해 가용성을 우선한다.
"""
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER, REFRESH_COOKIE

# 레이트리밋 면제 경로 — 헬스체크/문서는 카운트하지 않는다.
_RATELIMIT_EXEMPT_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")
# 인증 경로 — 토큰/코드 brute-force 방어를 위해 더 엄격한 별도 한도를 적용한다.
_AUTH_PREFIX = "/v1/auth"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """모든 응답에 기본 보안 헤더를 부착한다."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        # API 응답은 임베드/스크립트가 필요 없으므로 강한 CSP를 적용한다.
        headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
        # HTTPS 환경(운영)에서만 HSTS — http에선 브라우저가 무시하지만 명시적으로 분리.
        if settings.APP_ENV == "production":
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class CsrfMiddleware(BaseHTTPMiddleware):
    """쿠키 인증 요청에 대한 더블 서브밋 CSRF 검증.

    웹은 HttpOnly 쿠키로 인증하므로 SameSite=lax(1차) 외에 더블 서브밋 토큰(2차)을 요구한다.
    - 안전 메서드(GET/HEAD/OPTIONS)는 면제.
    - Bearer 헤더(모바일)로 인증하는 요청은 CSRF 비대상이라 면제.
    - 인증 쿠키가 실린 unsafe 요청만 X-CSRF-Token == csrf_token 쿠키 일치를 요구한다.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method not in _SAFE_METHODS:
            has_bearer = request.headers.get("authorization", "").startswith("Bearer ")
            cookie_auth = (
                ACCESS_COOKIE in request.cookies or REFRESH_COOKIE in request.cookies
            )
            if cookie_auth and not has_bearer:
                header_token = request.headers.get(CSRF_HEADER)
                cookie_token = request.cookies.get(CSRF_COOKIE)
                if (
                    not header_token
                    or not cookie_token
                    or not secrets.compare_digest(header_token, cookie_token)
                ):
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": {
                                "code": "CSRF_FAILED",
                                "message": "CSRF 토큰이 없거나 일치하지 않습니다.",
                                "status": 403,
                            }
                        },
                    )
        return await call_next(request)


class DemoModeMiddleware(BaseHTTPMiddleware):
    """데모 모드 — 공개 라이브 데모를 읽기전용으로 강제한다.

    DEMO_MODE=true일 때 모든 unsafe 메서드(POST/PATCH/PUT/DELETE)를 403으로 막는다.
    (Admin 대시보드 GET은 dependencies.get_admin_user가 인증 없이 열어주지만,
    쓰기 자체가 여기서 전부 차단되므로 공개돼도 안전하다.)
    """

    async def dispatch(self, request: Request, call_next):
        if settings.DEMO_MODE and request.method not in _SAFE_METHODS:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "DEMO_READONLY",
                        "message": "데모 모드에서는 쓰기 작업이 비활성화되어 있습니다.",
                        "status": 403,
                    }
                },
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP 기준 고정 윈도우 레이트리밋 (Redis). Redis 장애 시 통과(fail-open)."""

    def __init__(self, app, limit: int = 300, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds

    @staticmethod
    def _client_ip(request: Request) -> str:
        # 직접 연결 IP를 기본값으로 두고, 신뢰 프록시가 있을 때만 XFF를 해석한다.
        # XFF는 클라이언트가 위조할 수 있으므로 무조건 신뢰하면 레이트리밋이 무력화된다.
        direct = request.client.host if request.client else "unknown"
        hops = settings.TRUSTED_PROXY_COUNT
        if hops <= 0:
            return direct
        fwd = request.headers.get("x-forwarded-for")
        if not fwd:
            return direct
        parts = [p.strip() for p in fwd.split(",") if p.strip()]
        # 신뢰 프록시는 자신이 본 IP를 XFF 끝에 덧붙이므로, 끝에서 hops번째가 실제 클라이언트다.
        idx = len(parts) - hops
        if 0 <= idx < len(parts):
            return parts[idx]
        return parts[0] if parts else direct

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(_RATELIMIT_EXEMPT_PREFIXES):
            return await call_next(request)

        # 인증 경로는 더 낮은 한도 + 분리된 버킷을 사용한다.
        is_auth = path.startswith(_AUTH_PREFIX)
        limit = settings.AUTH_RATELIMIT_PER_MINUTE if is_auth else self.limit
        scope = "auth" if is_auth else "api"

        try:
            from app.redis import get_redis

            redis = await get_redis()
            ip = self._client_ip(request)
            bucket = int(__import__("time").time()) // self.window
            key = f"rl:{scope}:{ip}:{bucket}"
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, self.window)
            if count > limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                        }
                    },
                    headers={"Retry-After": str(self.window)},
                )
        except Exception:
            # Redis 불가 시 가용성 우선 — 통과시킨다.
            pass

        return await call_next(request)
