import asyncio
import os
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse")
# run_sync()가 호출마다 새 이벤트 루프를 생성하므로 NullPool로 커넥션 재사용을 막는다.
_engine = create_async_engine(database_url, poolclass=NullPool)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def _get_session() -> AsyncSession:
    return _SessionLocal()


async def create_batch_log(batch_id: str, scheduled_at: datetime) -> int:
    from app.models.batch import BatchLog, BatchStatus

    async with _get_session() as session:
        log = BatchLog(
            batch_id=batch_id,
            scheduled_at=scheduled_at,
            status=BatchStatus.SCHEDULED,
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log.id


async def mark_batch_running(batch_id: str) -> None:
    from app.models.batch import BatchLog, BatchStatus

    async with _get_session() as session:
        await session.execute(
            update(BatchLog)
            .where(BatchLog.batch_id == batch_id)
            .values(status=BatchStatus.RUNNING, started_at=datetime.now(UTC))
        )
        await session.commit()


async def mark_batch_completed(
    batch_id: str,
    *,
    collected_by_group: dict,
    deduplicated_count: int,
    published_by_type: dict,
    failed_count: int,
    api_tokens_used: int,
    api_cost_usd: Decimal,
    error_log: str | None = None,
) -> None:
    from app.models.batch import BatchLog, BatchStatus

    status = BatchStatus.COMPLETED
    if failed_count > 0 and (published_by_type.get("NEWS", 0) + published_by_type.get("TECHNIQUE", 0)) > 0:
        status = BatchStatus.PARTIAL_FAILURE
    elif failed_count > 0:
        status = BatchStatus.FAILED

    async with _get_session() as session:
        await session.execute(
            update(BatchLog)
            .where(BatchLog.batch_id == batch_id)
            .values(
                status=status,
                completed_at=datetime.now(UTC),
                collected_by_group=collected_by_group,
                deduplicated_count=deduplicated_count,
                published_by_type=published_by_type,
                failed_count=failed_count,
                api_tokens_used=api_tokens_used,
                api_cost_usd=api_cost_usd,
                error_log=error_log,
            )
        )
        await session.commit()


async def get_month_cost_usd(now: datetime | None = None) -> float:
    """이번 달(UTC) 배치 API 비용 합계 — 예산 하드 캡 판단용."""
    from app.models.batch import BatchLog
    from sqlalchemy import func, select

    now = now or datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    async with _get_session() as session:
        result = await session.execute(
            select(func.coalesce(func.sum(BatchLog.api_cost_usd), 0)).where(
                BatchLog.scheduled_at >= month_start
            )
        )
        return float(result.scalar_one())


async def mark_batch_failed(batch_id: str, error: str) -> None:
    from app.models.batch import BatchLog, BatchStatus

    async with _get_session() as session:
        await session.execute(
            update(BatchLog)
            .where(BatchLog.batch_id == batch_id)
            .values(
                status=BatchStatus.FAILED,
                completed_at=datetime.now(UTC),
                error_log=error,
            )
        )
        await session.commit()


def run_sync(coro):
    """Celery 태스크(동기)에서 async 함수 실행."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
