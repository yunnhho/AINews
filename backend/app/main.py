from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exceptions import AppError, app_error_handler, generic_exception_handler, http_exception_handler
from app.redis import close_redis, get_redis
from app.routers import admin, alerts, auth, cards, health, interactions, me, push, recommendations, search
from app.services.search import setup_index


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
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── 미들웨어 ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
