"""ALS 협업 필터링 모델 학습 Celery 태스크."""
import asyncio
import pickle
import time

import numpy as np
import redis.asyncio as aioredis
from celery.utils.log import get_task_logger
from scipy.sparse import csr_matrix
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pipeline.celery_app import app

logger = get_task_logger(__name__)

_DATABASE_URL = __import__("os").getenv(
    "DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse"
)
_REDIS_URL = __import__("os").getenv("REDIS_URL", "redis://redis:6379/0")

CF_MODEL_KEY = "cf:model_data"
_LIKE_WEIGHT = 1.0
_BOOKMARK_WEIGHT = 2.0

# asyncio.run()이 호출마다 새 이벤트 루프를 생성하므로 NullPool로 커넥션 재사용을 막는다.
_engine = create_async_engine(_DATABASE_URL, poolclass=NullPool)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@app.task(
    name="pipeline.tasks.train_cf.train_cf_model",
    queue="default",
)
def train_cf_model():
    """일 1회 ALS 협업 필터링 모델 재학습."""
    return asyncio.run(_async_train())


async def _async_train() -> dict:
    from app.models.user import UserBookmark, UserLike
    from implicit.als import AlternatingLeastSquares

    start = time.time()
    logger.info("CF 모델 학습 시작")

    async with _SessionLocal() as session:
        likes_result = await session.execute(select(UserLike.user_id, UserLike.card_id))
        bookmarks_result = await session.execute(select(UserBookmark.user_id, UserBookmark.card_id))
        likes = likes_result.fetchall()
        bookmarks = bookmarks_result.fetchall()

    interactions: dict[tuple[int, int], float] = {}
    for row in likes:
        key = (int(row.user_id), int(row.card_id))
        interactions[key] = interactions.get(key, 0.0) + _LIKE_WEIGHT
    for row in bookmarks:
        key = (int(row.user_id), int(row.card_id))
        interactions[key] = interactions.get(key, 0.0) + _BOOKMARK_WEIGHT

    if not interactions:
        logger.warning("상호작용 데이터 없음 — CF 모델 학습 건너뜀")
        return {"status": "skipped", "reason": "no_data"}

    user_ids = sorted({u for u, _ in interactions})
    card_ids = sorted({c for _, c in interactions})
    user_idx = {u: i for i, u in enumerate(user_ids)}
    card_idx = {c: i for i, c in enumerate(card_ids)}

    rows, cols, data = [], [], []
    for (uid, cid), w in interactions.items():
        rows.append(user_idx[uid])
        cols.append(card_idx[cid])
        data.append(w)

    # implicit(>=0.4)은 users × items 형태의 행렬을 fit()에 입력으로 받는다.
    # 이래야 model.user_factors가 user_ids 순서, item_factors가 card_ids 순서와 일치하여
    # recommendations._cf_recommendations의 (item_factors @ user_vec) 계산이 올바르다.
    user_item = csr_matrix(
        (data, (rows, cols)), shape=(len(user_ids), len(card_ids)), dtype=np.float32
    )

    model = AlternatingLeastSquares(
        factors=64, iterations=20, regularization=0.1, use_gpu=False
    )
    model.fit(user_item)

    elapsed = time.time() - start
    logger.info(
        "CF 모델 학습 완료 (%.1f초) — 사용자 %d명, 카드 %d장",
        elapsed,
        len(user_ids),
        len(card_ids),
    )

    model_data = {
        "user_ids": user_ids,
        "card_ids": card_ids,
        "user_factors": model.user_factors.tolist(),
        "item_factors": model.item_factors.tolist(),
        "trained_at": time.time(),
        "elapsed": elapsed,
    }
    payload = pickle.dumps(model_data)

    r = aioredis.from_url(_REDIS_URL, decode_responses=False)
    try:
        await r.set(CF_MODEL_KEY, payload, ex=86400 * 2)  # 2일 TTL
    finally:
        await r.aclose()

    logger.info("CF 모델 Redis 저장 완료 (크기=%d bytes)", len(payload))
    return {
        "status": "ok",
        "users": len(user_ids),
        "cards": len(card_ids),
        "elapsed": elapsed,
    }
