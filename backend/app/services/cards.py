import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card import Card, CardType, Category, Difficulty
from app.models.user import User, UserBookmark, UserLike
from app.redis import get_redis
from app.schemas.cards import FeedResponse, NewsCardResponse, TechniqueCardResponse

FEED_CACHE_TTL = 300  # 5분


def _cache_key(
    category: str,
    card_type: str,
    tags: list[str],
    difficulty: str,
    cursor: str,
    limit: int,
) -> str:
    tags_str = ",".join(sorted(tags))
    return f"feed:{category}:{card_type}:{tags_str}:{difficulty}:{cursor}:{limit}"


def _serialize_card(card: Card, liked_ids: set[int], bookmarked_ids: set[int]) -> dict:
    data = {
        "id": card.id,
        "card_type": card.card_type.value,
        "category": card.category.value,
        "difficulty": card.difficulty.value,
        "title": card.title,
        "summary": card.summary,
        "source_url": card.source_url,
        "source_name": card.source_name,
        "source_group": card.source_group.value,
        "original_lang": card.original_lang.value,
        "thumbnail_url": card.thumbnail_url,
        "like_count": card.like_count,
        "bookmark_count": card.bookmark_count,
        "published_at": card.published_at.isoformat(),
        "tags": [{"id": t.id, "name": t.name, "slug": t.slug} for t in (card.tags or [])],
        "is_liked": card.id in liked_ids,
        "is_bookmarked": card.id in bookmarked_ids,
    }
    if card.card_type == CardType.NEWS:
        data["key_points"] = card.key_points
    else:
        data.update(
            problem=card.problem,
            idea=card.idea,
            code_snippet=card.code_snippet,
            caveats=card.caveats,
            prerequisites=card.prerequisites,
        )
    return data


async def get_feed(
    db: AsyncSession,
    current_user: User | None,
    category: str = "all",
    card_type: str = "all",
    tags: list[str] | None = None,
    difficulty: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> FeedResponse:
    tags = tags or []
    limit = min(limit, 50)

    cache_key = _cache_key(
        category, card_type, tags, difficulty or "", cursor or "", limit
    )
    redis = await get_redis()

    cached = await redis.get(cache_key)
    if cached:
        raw = json.loads(cached)
        liked_ids: set[int] = set()
        bookmarked_ids: set[int] = set()
        if current_user:
            liked_ids, bookmarked_ids = await _get_user_interaction_ids(db, current_user.id)
        items = _build_response_items(raw["items"], liked_ids, bookmarked_ids)
        return FeedResponse(items=items, next_cursor=raw["next_cursor"], has_more=raw["has_more"])

    stmt = (
        select(Card)
        .options(selectinload(Card.tags))
        .where(Card.is_published.is_(True))
        .order_by(Card.published_at.desc())
    )

    if category != "all":
        stmt = stmt.where(Card.category == Category(category))
    if card_type != "all":
        stmt = stmt.where(Card.card_type == CardType(card_type))
    if difficulty:
        stmt = stmt.where(Card.difficulty == Difficulty(difficulty))
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            stmt = stmt.where(Card.published_at < cursor_dt)
        except ValueError:
            pass
    if tags:
        from app.models.card import CardTag, Tag
        for slug in tags:
            tag_sub = select(CardTag.card_id).join(Tag).where(Tag.slug == slug)
            stmt = stmt.where(Card.id.in_(tag_sub))

    stmt = stmt.limit(limit + 1)
    result = await db.execute(stmt)
    cards = list(result.scalars().all())

    has_more = len(cards) > limit
    if has_more:
        cards = cards[:limit]

    next_cursor = cards[-1].published_at.isoformat() if (has_more and cards) else None

    serialized = [_serialize_card(c, set(), set()) for c in cards]
    await redis.setex(cache_key, FEED_CACHE_TTL, json.dumps({"items": serialized, "next_cursor": next_cursor, "has_more": has_more}))

    liked_ids = set()
    bookmarked_ids = set()
    if current_user:
        liked_ids, bookmarked_ids = await _get_user_interaction_ids(db, current_user.id)

    items = _build_response_items(serialized, liked_ids, bookmarked_ids)
    return FeedResponse(items=items, next_cursor=next_cursor, has_more=has_more)


async def _get_user_interaction_ids(db: AsyncSession, user_id: int) -> tuple[set[int], set[int]]:
    likes_result = await db.execute(select(UserLike.card_id).where(UserLike.user_id == user_id))
    bookmarks_result = await db.execute(select(UserBookmark.card_id).where(UserBookmark.user_id == user_id))
    return set(likes_result.scalars()), set(bookmarks_result.scalars())


def _build_response_items(
    raw_items: list[dict],
    liked_ids: set[int],
    bookmarked_ids: set[int],
) -> list[NewsCardResponse | TechniqueCardResponse]:
    items = []
    for d in raw_items:
        d = {**d, "is_liked": d["id"] in liked_ids, "is_bookmarked": d["id"] in bookmarked_ids}
        if d["card_type"] == CardType.NEWS.value:
            items.append(NewsCardResponse(**d))
        else:
            items.append(TechniqueCardResponse(**d))
    return items


async def get_card_by_id(
    db: AsyncSession,
    card_id: int,
    current_user: User | None,
) -> NewsCardResponse | TechniqueCardResponse:
    result = await db.execute(
        select(Card)
        .options(selectinload(Card.tags))
        .where(Card.id == card_id, Card.is_published.is_(True))
    )
    card = result.scalar_one_or_none()
    if card is None:
        from app.exceptions import NotFoundError
        raise NotFoundError("카드")

    liked_ids: set[int] = set()
    bookmarked_ids: set[int] = set()
    if current_user:
        liked_ids, bookmarked_ids = await _get_user_interaction_ids(db, current_user.id)

    data = _serialize_card(card, liked_ids, bookmarked_ids)
    if card.card_type == CardType.NEWS:
        return NewsCardResponse(**data)
    return TechniqueCardResponse(**data)
