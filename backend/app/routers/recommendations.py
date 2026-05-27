from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.cards import FeedResponse
from app.services import recommendations as rec_svc

router = APIRouter(prefix="/v1/cards", tags=["recommendations"])


@router.get("/recommended", response_model=FeedResponse)
async def get_recommended(
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await rec_svc.get_recommendations(db, current_user, limit=limit)
