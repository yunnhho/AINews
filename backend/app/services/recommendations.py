"""규칙 기반 추천 피드 — 카테고리·태그·card_type 빈도 집계."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card import Card, Category
from app.models.user import User, UserBookmark, UserLike
from app.schemas.cards import FeedResponse
from app.services.cards import _build_response_items, _serialize_card

_HISTORY_DAYS = 30
_MAIN_RATIO = 0.8


async def get_recommendations(db: AsyncSession, current_user: User, limit: int = 20) -> FeedResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_HISTORY_DAYS)

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
    interacted_ids = set(likes_result.scalars()) | set(bookmarks_result.scalars())

    # 빈도 집계
    category_counter: Counter = Counter()
    if interacted_ids:
        hist_result = await db.execute(
            select(Card.category).where(Card.id.in_(interacted_ids))
        )
        category_counter = Counter(r for r in hist_result.scalars())

    main_limit = max(1, int(limit * _MAIN_RATIO))
    diversity_limit = limit - main_limit

    # 80% — 상위 카테고리 최신 카드
    main_cards: list[Card] = []
    touched_categories: set[Category] = set(category_counter.keys())

    if category_counter:
        top_cats = [cat for cat, _ in category_counter.most_common(2)]
        stmt = (
            select(Card)
            .options(selectinload(Card.tags))
            .where(Card.category.in_(top_cats))
            .order_by(Card.published_at.desc())
            .limit(main_limit)
        )
        if interacted_ids:
            stmt = stmt.where(Card.id.notin_(interacted_ids))
        result = await db.execute(stmt)
        main_cards = list(result.scalars())

    # 20% — 미접촉 카테고리 인기 카드
    untouched = set(Category) - touched_categories
    diversity_cards: list[Card] = []
    if untouched:
        stmt = (
            select(Card)
            .options(selectinload(Card.tags))
            .where(Card.category.in_(untouched))
            .order_by(Card.like_count.desc(), Card.published_at.desc())
            .limit(diversity_limit)
        )
        if interacted_ids:
            stmt = stmt.where(Card.id.notin_(interacted_ids))
        result = await db.execute(stmt)
        diversity_cards = list(result.scalars())

    combined = main_cards + diversity_cards

    # 부족하면 인기 카드로 채움
    if len(combined) < limit:
        filled_ids = {c.id for c in combined} | interacted_ids
        fallback = (
            select(Card)
            .options(selectinload(Card.tags))
            .order_by(Card.like_count.desc(), Card.published_at.desc())
            .limit(limit - len(combined))
        )
        if filled_ids:
            fallback = fallback.where(Card.id.notin_(filled_ids))
        result = await db.execute(fallback)
        combined.extend(result.scalars())

    # 사용자 인터랙션 전체 목록
    all_likes = await db.execute(select(UserLike.card_id).where(UserLike.user_id == current_user.id))
    all_bookmarks = await db.execute(select(UserBookmark.card_id).where(UserBookmark.user_id == current_user.id))
    liked_ids = set(all_likes.scalars())
    bookmarked_ids = set(all_bookmarks.scalars())

    serialized = [_serialize_card(c, liked_ids, bookmarked_ids) for c in combined]
    items = _build_response_items(serialized, liked_ids, bookmarked_ids)
    return FeedResponse(items=items, next_cursor=None, has_more=False)
