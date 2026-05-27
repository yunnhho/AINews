"""source_health 테이블 조회·업데이트 헬퍼."""
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse")
_engine = create_async_engine(database_url, pool_pre_ping=True)
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


def run_sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
