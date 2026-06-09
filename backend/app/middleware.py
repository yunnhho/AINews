"""기본 보안 미들웨어 — 보안 헤더 + IP 기반 레이트리밋.

운영 환경(APP_ENV=production)에서만 HSTS를 켜고, 레이트리밋은 Redis 장애 시
요청을 막지 않도록(fail-open) 설계해 가용성을 우선한다.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

# 레이트리밋 면제 경로 — 헬스체크/문서는 카운트하지 않는다.
_RATELIMIT_EXEMPT_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")


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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP 기준 고정 윈도우 레이트리밋 (Redis). Redis 장애 시 통과(fail-open)."""

    def __init__(self, app, limit: int = 300, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds

    @staticmethod
    def _client_ip(request: Request) -> str:
        # 프록시 뒤(운영)에서는 X-Forwarded-For의 첫 IP를 사용.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(_RATELIMIT_EXEMPT_PREFIXES):
            return await call_next(request)

        try:
            from app.redis import get_redis

            redis = await get_redis()
            ip = self._client_ip(request)
            bucket = int(__import__("time").time()) // self.window
            key = f"rl:{ip}:{bucket}"
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, self.window)
            if count > self.limit:
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
