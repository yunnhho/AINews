"""배치 완료 후 소스 상태 점검 및 경보 발송."""
import asyncio
import os

import redis.asyncio as aioredis
from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pipeline.celery_app import app

logger = get_task_logger(__name__)

_database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse")
_redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

# asyncio.run()이 호출마다 새 이벤트 루프를 생성하므로 NullPool로 커넥션 재사용을 막는다.
_engine = create_async_engine(_database_url, poolclass=NullPool)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@app.task(
    name="pipeline.tasks.check_source_health.check_and_alert",
    queue="default",
)
def check_and_alert():
    """배치 완료 후 소스 상태 점검 + 경보 발송."""
    asyncio.run(_async_check())


async def _async_check() -> None:
    from app.services.alerting import check_and_alert as _check

    # 각 태스크 호출마다 독립 Redis 연결을 생성 (이벤트 루프 충돌 방지)
    redis = aioredis.from_url(_redis_url, decode_responses=True)
    try:
        async with _SessionLocal() as session:
            await _check(session, redis=redis)
    except Exception as exc:
        logger.error(f"소스 상태 점검 중 오류: {exc}", exc_info=True)
    finally:
        await redis.aclose()
