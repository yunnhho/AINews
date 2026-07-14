"""source_health 테이블 조회·업데이트 헬퍼."""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.db import SessionLocal, run_sync  # noqa: F401 — run_sync는 호출부 재수출용


def _get_session() -> AsyncSession:
    return SessionLocal()


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
        health.last_success_at = datetime.now(UTC)
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


async def get_disabled_sources() -> frozenset[str]:
    """비활성화된 소스 이름 전체를 한 번의 쿼리로 반환한다."""
    from app.models.batch import SourceHealth

    async with _get_session() as session:
        result = await session.execute(
            select(SourceHealth.source_name).where(SourceHealth.enabled == False)  # noqa: E712
        )
        return frozenset(row[0] for row in result.fetchall())
