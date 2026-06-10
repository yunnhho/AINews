"""협업 필터링(ALS) + 규칙 기반 폴백 추천 피드.

CF 모델이 Redis에 없거나 사용자 상호작용이 부족하면 P1-4 규칙 기반 로직으로 폴백한다.
"""
import logging
import pickle
from collections import Counter
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card import Card, Category
from app.models.user import User, UserBookmark, UserLike
from app.redis import get_redis_binary
from app.schemas.cards import FeedResponse
from app.services.cards import _build_response_items, _serialize_card

logger = logging.getLogger(__name__)

_HISTORY_DAYS = 30
_MAIN_RATIO = 0.8
_CF_MODEL_KEY = "cf:model_data"
_MIN_INTERACTIONS_FOR_CF = 5  # cold start 임계값


async def _load_cf_model() -> dict | None:
    """Redis에서 CF 모델 데이터(user_factors, item_factors, id 매핑) 로드."""
    try:
        redis = await get_redis_binary()
        raw = await redis.get(_CF_MODEL_KEY)
        if raw is None:
            return None
        return pickle.loads(raw)  # noqa: S301
    except Exception as exc:
        logger.warning("CF 모델 로드 실패: %s", exc)
        return None


async def _cf_recommendations(
    db: AsyncSession,
    user: User,
    model_data: dict,
    limit: int,
    interacted_ids: set[int],
) -> list[Card] | None:
    """ALS 모델 기반 Top-K 추천. 사용자가 모델에 없으면 None 반환(cold start)."""
    user_ids: list[int] = model_data["user_ids"]
    card_ids: list[int] = model_data["card_ids"]

    if user.id not in user_ids:
        return None  # cold start — 모델 학습 시점에 상호작용 이력 없던 사용자

    user_factors = np.array(model_data["user_factors"], dtype=np.float32)
    item_factors = np.array(model_data["item_factors"], dtype=np.float32)

    user_idx = user_ids.index(user.id)
    user_vec = user_factors[user_idx]  # (factors,)

    # ALS 스코어: dot product of user vector and item matrix
    scores = item_factors @ user_vec  # (n_items,)

    # 이미 상호작용한 카드 마스킹
    card_id_to_idx = {cid: i for i, cid in enumerate(card_ids)}
    for cid in interacted_ids:
        if cid in card_id_to_idx:
            scores[card_id_to_idx[cid]] = -np.inf

    top_indices = np.argsort(scores)[::-1][: limit * 2]
    recommended_ids = [card_ids[i] for i in top_indices if scores[i] > -np.inf][:limit]

    if not recommended_ids:
        return None

    result = await db.execute(
        select(Card)
        .options(selectinload(Card.tags))
        .where(Card.id.in_(recommended_ids), Card.is_published.is_(True))
    )
    card_map = {c.id: c for c in result.scalars()}
    # 추천 순서 보존
    return [card_map[cid] for cid in recommended_ids if cid in card_map]


async def _rule_based_recommendations(
    db: AsyncSession,
    current_user: User,
    limit: int,
    interacted_ids: set[int],
) -> list[Card]:
    """P1-4 규칙 기반 추천 — 카테고리 빈도 80% + 다양성 20%."""
    cutoff = datetime.now(UTC) - timedelta(days=_HISTORY_DAYS)

    likes_result = await db.execute(
        select(UserLike.card_id).where(
            UserLike.user_id == current_user.id, UserLike.created_at >= cutoff
        )
    )
    bookmarks_result = await db.execute(
        select(UserBookmark.card_id).where(
            UserBookmark.user_id == current_user.id, UserBookmark.created_at >= cutoff
        )
    )
    recent_ids = set(likes_result.scalars()) | set(bookmarks_result.scalars())

    category_counter: Counter = Counter()
    if recent_ids:
        hist_result = await db.execute(
            select(Card.category).where(Card.id.in_(recent_ids))
        )
        category_counter = Counter(r for r in hist_result.scalars())

    main_limit = max(1, int(limit * _MAIN_RATIO))
    diversity_limit = limit - main_limit
    touched_categories: set[Category] = set(category_counter.keys())

    # 80% — 상위 카테고리 최신 카드
    main_cards: list[Card] = []
    if category_counter:
        top_cats = [cat for cat, _ in category_counter.most_common(2)]
        stmt = (
            select(Card)
            .options(selectinload(Card.tags))
            .where(Card.category.in_(top_cats), Card.is_published.is_(True))
            .order_by(Card.published_at.desc())
            .limit(main_limit)
        )
        if interacted_ids:
            stmt = stmt.where(Card.id.notin_(interacted_ids))
        result = await db.execute(stmt)
        main_cards = list(result.scalars())

    # 20% — 미접촉 카테고리 인기 카드 (필터 버블 방지)
    untouched = set(Category) - touched_categories
    diversity_cards: list[Card] = []
    if untouched:
        stmt = (
            select(Card)
            .options(selectinload(Card.tags))
            .where(Card.category.in_(untouched), Card.is_published.is_(True))
            .order_by(Card.like_count.desc(), Card.published_at.desc())
            .limit(diversity_limit)
        )
        if interacted_ids:
            stmt = stmt.where(Card.id.notin_(interacted_ids))
        result = await db.execute(stmt)
        diversity_cards = list(result.scalars())

    combined = main_cards + diversity_cards

    # 부족하면 전체 인기 카드로 채움
    if len(combined) < limit:
        filled_ids = {c.id for c in combined} | interacted_ids
        fallback = (
            select(Card)
            .options(selectinload(Card.tags))
            .where(Card.is_published.is_(True))
            .order_by(Card.like_count.desc(), Card.published_at.desc())
            .limit(limit - len(combined))
        )
        if filled_ids:
            fallback = fallback.where(Card.id.notin_(filled_ids))
        result = await db.execute(fallback)
        combined.extend(result.scalars())

    return combined


async def get_recommendations(db: AsyncSession, current_user: User, limit: int = 20) -> FeedResponse:
    all_likes = await db.execute(
        select(UserLike.card_id).where(UserLike.user_id == current_user.id)
    )
    all_bookmarks = await db.execute(
        select(UserBookmark.card_id).where(UserBookmark.user_id == current_user.id)
    )
    liked_ids = set(all_likes.scalars())
    bookmarked_ids = set(all_bookmarks.scalars())
    interacted_ids = liked_ids | bookmarked_ids

    combined: list[Card] = []

    # CF 추천 시도: 상호작용 5건 이상이고 Redis 모델 존재 시
    if len(interacted_ids) >= _MIN_INTERACTIONS_FOR_CF:
        model_data = await _load_cf_model()
        if model_data is not None:
            cf_result = await _cf_recommendations(
                db, current_user, model_data, limit, interacted_ids
            )
            if cf_result:
                combined = cf_result

    # cold start 또는 CF 실패 → 규칙 기반 폴백
    if not combined:
        combined = await _rule_based_recommendations(db, current_user, limit, interacted_ids)

    serialized = [_serialize_card(c, liked_ids, bookmarked_ids) for c in combined]
    items = _build_response_items(serialized, liked_ids, bookmarked_ids)
    return FeedResponse(items=items, next_cursor=None, has_more=False)
