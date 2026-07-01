from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.exceptions import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
)
from app.middleware import (
    CsrfMiddleware,
    DemoModeMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.redis import close_redis, get_redis
from app.routers import (
    admin,
    alerts,
    auth,
    cards,
    health,
    interactions,
    me,
    push,
    recommendations,
    search,
)
from app.services.search import setup_index

_IS_PROD = settings.APP_ENV == "production"

# 운영 환경에서 시크릿이 기본값이면 부팅 차단 (토큰 위조 방지).
if _IS_PROD:
    for _name, _val in (("SECRET_KEY", settings.SECRET_KEY), ("JWT_SECRET", settings.JWT_SECRET)):
        if _val in ("", "change-me"):
            raise RuntimeError(f"{_name}가 기본값입니다. 운영 환경에서는 강한 시크릿을 설정하세요.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_redis()
    try:
        await setup_index()
    except Exception:
        pass  # Elasticsearch가 없어도 앱은 기동
    yield
    await close_redis()


app = FastAPI(
    title="AI Pulse API",
    version="1.0.0",
    # 운영 환경에서는 API 문서를 노출하지 않는다 (정보 노출 최소화).
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
    lifespan=lifespan,
)

# ── 미들웨어 ──────────────────────────────────────
# 운영 환경에서만 Host 헤더 검증 (Host 헤더 주입 방어). 개발은 임의 호스트 허용.
if _IS_PROD:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list,
    )

app.add_middleware(SecurityHeadersMiddleware)
# 데모 모드에서 쓰기 요청을 전역 차단(공개 라이브 데모 안전장치). CORS 안쪽에 위치.
app.add_middleware(DemoModeMiddleware)
app.add_middleware(CsrfMiddleware)
app.add_middleware(RateLimitMiddleware, limit=settings.RATELIMIT_PER_MINUTE, window_seconds=60)

# 쿠키 인증(allow_credentials=True)이므로 메서드/헤더는 실제 사용하는 것만 화이트리스트.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

# ── 에러 핸들러 ───────────────────────────────────
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ── 라우터 ────────────────────────────────────────
# 주의: recommended·interactions는 cards 라우터의 /{card_id} 보다 먼저 등록해야 함
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(recommendations.router)
app.include_router(interactions.router)
app.include_router(me.router)
app.include_router(search.router)
app.include_router(cards.router)
app.include_router(admin.router)
app.include_router(alerts.router)
app.include_router(push.router)
