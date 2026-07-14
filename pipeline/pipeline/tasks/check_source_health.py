"""배치 완료 후 소스 상태 점검 및 경보 발송."""
import asyncio
import os

import redis.asyncio as aioredis
from celery.utils.log import get_task_logger

from pipeline.celery_app import app
from pipeline.db import SessionLocal as _SessionLocal

logger = get_task_logger(__name__)

_redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")


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
