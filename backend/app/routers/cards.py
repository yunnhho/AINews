from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import optional_user
from app.models.user import User
from app.schemas.cards import FeedResponse, NewsCardResponse, TechniqueCardResponse
from app.services import cards as cards_svc

router = APIRouter(prefix="/v1/cards", tags=["cards"])


@router.get("", response_model=FeedResponse)
async def list_cards(
    category: str = Query(default="all"),
    card_type: str = Query(default="all"),
    tags: list[str] = Query(default=[]),
    difficulty: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(optional_user),
):
    return await cards_svc.get_feed(
        db=db,
        current_user=current_user,
        category=category,
        card_type=card_type,
        tags=tags,
        difficulty=difficulty,
        cursor=cursor,
        limit=limit,
    )


@router.get("/{card_id}", response_model=NewsCardResponse | TechniqueCardResponse)
async def get_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(optional_user),
):
    return await cards_svc.get_card_by_id(db=db, card_id=card_id, current_user=current_user)
