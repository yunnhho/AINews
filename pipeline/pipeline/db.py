"""파이프라인 공용 DB 세션 + 동기 실행 헬퍼.

run_sync()/asyncio.run()이 호출마다 새 이벤트 루프를 생성하므로, 풀에 캐시된
asyncpg 커넥션이 닫힌 루프에 묶여 재사용 시 깨진다. NullPool로 매번 새 커넥션 생성.
"""
import asyncio
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse"
)
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def run_sync(coro):
    """Celery 태스크(동기)에서 async 함수 실행."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
