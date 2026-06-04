from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.card import Card, CardType, Category
from app.models.user import User, UserBookmark, UserLike
from app.schemas.cards import FeedResponse
from app.services.cards import _build_response_items, _serialize_card

router = APIRouter(prefix="/v1/me", tags=["me"])


@router.get("/bookmarks", response_model=FeedResponse)
async def get_my_bookmarks(
    category: str = Query(default="all"),
    card_type: str = Query(default="all"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 북마크된 카드 ID 목록
    bm_result = await db.execute(
        select(UserBookmark.card_id).where(UserBookmark.user_id == current_user.id)
    )
    bookmarked_card_ids = list(bm_result.scalars())

    if not bookmarked_card_ids:
        return FeedResponse(items=[], next_cursor=None, has_more=False)

    stmt = (
        select(Card)
        .options(selectinload(Card.tags))
        .where(Card.id.in_(bookmarked_card_ids), Card.is_published.is_(True))
        .order_by(Card.published_at.desc())
    )

    if category != "all":
        stmt = stmt.where(Card.category == Category(category))
    if card_type != "all":
        stmt = stmt.where(Card.card_type == CardType(card_type))
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            stmt = stmt.where(Card.published_at < cursor_dt)
        except ValueError:
            pass

    stmt = stmt.limit(limit + 1)
    result = await db.execute(stmt)
    cards = list(result.scalars())

    has_more = len(cards) > limit
    if has_more:
        cards = cards[:limit]
    next_cursor = cards[-1].published_at.isoformat() if (has_more and cards) else None

    likes_result = await db.execute(
        select(UserLike.card_id).where(UserLike.user_id == current_user.id)
    )
    liked_ids = set(likes_result.scalars())
    bookmarked_ids = set(bookmarked_card_ids)

    serialized = [_serialize_card(c, liked_ids, bookmarked_ids) for c in cards]
    items = _build_response_items(serialized, liked_ids, bookmarked_ids)
    return FeedResponse(items=items, next_cursor=next_cursor, has_more=has_more)
