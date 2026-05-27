"""좋아요·북마크 처리 + like_count/bookmark_count 동기 업데이트."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.models.card import Card
from app.models.user import UserBookmark, UserLike


async def like_card(db: AsyncSession, user_id: int, card_id: int) -> None:
    card = await db.get(Card, card_id)
    if card is None:
        raise NotFoundError("카드")

    existing = await db.execute(
        select(UserLike).where(UserLike.user_id == user_id, UserLike.card_id == card_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("ALREADY_LIKED", "이미 좋아요한 카드입니다.")

    db.add(UserLike(user_id=user_id, card_id=card_id))
    await db.execute(update(Card).where(Card.id == card_id).values(like_count=Card.like_count + 1))
    await db.commit()


async def unlike_card(db: AsyncSession, user_id: int, card_id: int) -> None:
    result = await db.execute(
        select(UserLike).where(UserLike.user_id == user_id, UserLike.card_id == card_id)
    )
    like = result.scalar_one_or_none()
    if like is None:
        raise NotFoundError("좋아요")

    await db.delete(like)
    await db.execute(
        update(Card).where(Card.id == card_id, Card.like_count > 0).values(like_count=Card.like_count - 1)
    )
    await db.commit()


async def bookmark_card(db: AsyncSession, user_id: int, card_id: int) -> None:
    card = await db.get(Card, card_id)
    if card is None:
        raise NotFoundError("카드")

    existing = await db.execute(
        select(UserBookmark).where(UserBookmark.user_id == user_id, UserBookmark.card_id == card_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("ALREADY_BOOKMARKED", "이미 북마크한 카드입니다.")

    db.add(UserBookmark(user_id=user_id, card_id=card_id))
    await db.execute(
        update(Card).where(Card.id == card_id).values(bookmark_count=Card.bookmark_count + 1)
    )
    await db.commit()


async def unbookmark_card(db: AsyncSession, user_id: int, card_id: int) -> None:
    result = await db.execute(
        select(UserBookmark).where(UserBookmark.user_id == user_id, UserBookmark.card_id == card_id)
    )
    bookmark = result.scalar_one_or_none()
    if bookmark is None:
        raise NotFoundError("북마크")

    await db.delete(bookmark)
    await db.execute(
        update(Card)
        .where(Card.id == card_id, Card.bookmark_count > 0)
        .values(bookmark_count=Card.bookmark_count - 1)
    )
    await db.commit()
