"""배치 완료 후 Expo Push 알림 발송 태스크."""
import asyncio
import os

from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pipeline.celery_app import app

logger = get_task_logger(__name__)

_database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse")
# asyncio.run()이 호출마다 새 이벤트 루프를 생성하므로 NullPool로 커넥션 재사용을 막는다.
_engine = create_async_engine(_database_url, poolclass=NullPool)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@app.task(
    name="pipeline.tasks.send_push.send_batch_push",
    queue="default",
)
def send_batch_push(news_count: int = 0, tech_count: int = 0):
    """배치 완료 후 활성화된 디바이스에 푸시 알림 발송."""
    if news_count + tech_count == 0:
        return
    asyncio.run(_async_send(news_count, tech_count))


async def _async_send(news_count: int, tech_count: int) -> None:
    from app.services.push import get_enabled_tokens, send_batch_complete_notification

    try:
        async with _SessionLocal() as session:
            tokens = await get_enabled_tokens(session)

        if not tokens:
            logger.info("알림 활성화된 디바이스 없음 — 발송 생략")
            return

        await send_batch_complete_notification(tokens, news_count, tech_count)
    except Exception as exc:
        logger.error(f"푸시 알림 발송 중 오류: {exc}", exc_info=True)
