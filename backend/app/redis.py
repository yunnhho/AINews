from redis.asyncio import Redis, from_url

from app.config import settings

_redis: Redis | None = None
_redis_binary: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def get_redis_binary() -> Redis:
    """피클 직렬화 데이터(CF 모델 등) 저장용 바이너리 Redis 클라이언트."""
    global _redis_binary
    if _redis_binary is None:
        _redis_binary = from_url(settings.REDIS_URL, decode_responses=False)
    return _redis_binary


async def close_redis() -> None:
    global _redis, _redis_binary
    if _redis is not None:
        await _redis.aclose()
        _redis = None
    if _redis_binary is not None:
        await _redis_binary.aclose()
        _redis_binary = None
