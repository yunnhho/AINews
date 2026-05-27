from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import interactions as interactions_svc

router = APIRouter(prefix="/v1/cards", tags=["interactions"])


@router.post("/{card_id}/like", status_code=204)
async def like_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await interactions_svc.like_card(db, current_user.id, card_id)


@router.delete("/{card_id}/like", status_code=204)
async def unlike_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await interactions_svc.unlike_card(db, current_user.id, card_id)


@router.post("/{card_id}/bookmark", status_code=204)
async def bookmark_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await interactions_svc.bookmark_card(db, current_user.id, card_id)


@router.delete("/{card_id}/bookmark", status_code=204)
async def unbookmark_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await interactions_svc.unbookmark_card(db, current_user.id, card_id)
