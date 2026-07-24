import json
from datetime import datetime

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card import Card, CardType, Category, Difficulty
from app.models.user import User, UserBookmark, UserLike
from app.redis import get_redis
from app.schemas.cards import FeedResponse, NewsCardResponse, TechniqueCardResponse

FEED_CACHE_TTL = 300  # 5분
_FEED_VERSION_KEY = "feed:ver"  # 피드 캐시 네임스페이스 버전 (발행 시 INCR로 일괄 무효화)


async def _feed_version(redis) -> str:
    """현재 피드 캐시 버전. 없으면 '0'. 모든 캐시 키에 접두어로 붙는다."""
    v = await redis.get(_FEED_VERSION_KEY)
    return v if v is not None else "0"


async def invalidate_feed_cache() -> None:
    """피드 캐시 전체 무효화 — 버전을 올려 기존 키 네임스페이스를 통째로 폐기한다.

    조합 폭발한 키를 SCAN/DEL로 훑지 않고 O(1)로 무효화한다(기존 키는 TTL로 자연 소멸).
    카드 발행/삭제 등 피드 내용이 바뀌는 시점에 호출한다. best-effort: 실패해도 TTL이 방어한다.
    """
    try:
        redis = await get_redis()
        await redis.incr(_FEED_VERSION_KEY)
    except Exception:
        pass


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


def _encode_cursor(card: Card) -> str:
    """복합 커서 = published_at + id. 동일 published_at 동점에서도 안정적으로 이어진다."""
    return f"{card.published_at.isoformat()}|{card.id}"


def _decode_cursor(cursor: str) -> tuple[datetime, int | None] | None:
    """커서 문자열을 (published_at, id)로 파싱.

    - 신규 형식 'ISO|id' → (datetime, id)
    - 구(舊) 형식 'ISO'(id 없음) → (datetime, None)  ← 하위호환
    - 파싱 불가 → None (커서 무시하고 첫 페이지)
    """
    ts_part, _, id_part = cursor.rpartition("|")
    if ts_part:  # 'ISO|id' 형식
        try:
            return datetime.fromisoformat(ts_part), int(id_part)
        except ValueError:
            return None
    try:  # 구 형식(타임스탬프 단독)
        return datetime.fromisoformat(id_part), None
    except ValueError:
        return None


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

    redis = await get_redis()
    cache_key = f"{await _feed_version(redis)}:" + _cache_key(
        category, card_type, tags, difficulty or "", cursor or "", limit
    )

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
        # 복합 정렬: 동일 published_at 동점을 id로 타이브레이크해 커서 경계에서 행 누락/중복을 막는다.
        .order_by(Card.published_at.desc(), Card.id.desc())
    )

    if category != "all":
        stmt = stmt.where(Card.category == Category(category))
    if card_type != "all":
        stmt = stmt.where(Card.card_type == CardType(card_type))
    if difficulty:
        stmt = stmt.where(Card.difficulty == Difficulty(difficulty))
    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded is not None:
            cursor_dt, cursor_id = decoded
            if cursor_id is not None:
                # (published_at, id) 튜플 비교 — DESC 순에서 커서보다 "뒤"의 행만.
                stmt = stmt.where(tuple_(Card.published_at, Card.id) < (cursor_dt, cursor_id))
            else:
                # 구 형식 커서(타임스탬프 단독) 하위호환 — 동점 경계는 보장 못 하나 동작은 유지.
                stmt = stmt.where(Card.published_at < cursor_dt)
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

    next_cursor = _encode_cursor(cards[-1]) if (has_more and cards) else None

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
