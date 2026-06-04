"""source_health 테이블 조회·업데이트 헬퍼."""
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse")
# run_sync()가 호출마다 새 이벤트 루프를 생성하므로, 풀에 캐시된 asyncpg 커넥션이
# 닫힌 루프에 묶여 재사용 시 깨진다. NullPool로 매 체크아웃마다 현재 루프에서 새 커넥션 생성.
_engine = create_async_engine(database_url, poolclass=NullPool)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def _get_session() -> AsyncSession:
    return _SessionLocal()


async def record_success(source_name: str, source_group: str) -> None:
    from app.models.batch import SourceHealth

    async with _get_session() as session:
        result = await session.execute(
            select(SourceHealth).where(SourceHealth.source_name == source_name)
        )
        health = result.scalar_one_or_none()
        if health is None:
            health = SourceHealth(
                source_name=source_name,
                source_group=source_group,
                consecutive_failures=0,
                enabled=True,
            )
            session.add(health)
        else:
            health.consecutive_failures = 0
            health.last_error_log = None
        health.last_success_at = datetime.now(timezone.utc)
        await session.commit()


async def record_failure(source_name: str, source_group: str, error: str, disable_on_404: bool = False) -> None:
    from app.models.batch import SourceHealth

    async with _get_session() as session:
        result = await session.execute(
            select(SourceHealth).where(SourceHealth.source_name == source_name)
        )
        health = result.scalar_one_or_none()
        if health is None:
            health = SourceHealth(
                source_name=source_name,
                source_group=source_group,
                consecutive_failures=1,
                last_error_log=error,
                enabled=not disable_on_404,
            )
            session.add(health)
        else:
            health.consecutive_failures += 1
            health.last_error_log = error
            if disable_on_404:
                health.enabled = False
        await session.commit()


async def is_enabled(source_name: str) -> bool:
    from app.models.batch import SourceHealth

    async with _get_session() as session:
        result = await session.execute(
            select(SourceHealth.enabled).where(SourceHealth.source_name == source_name)
        )
        val = result.scalar_one_or_none()
        return val if val is not None else True


async def get_disabled_sources() -> frozenset[str]:
    """비활성화된 소스 이름 전체를 한 번의 쿼리로 반환한다."""
    from app.models.batch import SourceHealth

    async with _get_session() as session:
        result = await session.execute(
            select(SourceHealth.source_name).where(SourceHealth.enabled == False)  # noqa: E712
        )
        return frozenset(row[0] for row in result.fetchall())


def run_sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
