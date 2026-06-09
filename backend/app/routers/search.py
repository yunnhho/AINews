from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import optional_user
from app.models.user import User
from app.schemas.search import SearchResponse
from app.services import search as search_svc

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search_cards(
    q: str = Query(..., min_length=1, description="검색어"),
    category: str | None = Query(default=None),
    card_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(optional_user),
):
    result = await search_svc.search_cards(
        q, category, card_type, limit, offset, db=db, current_user=current_user
    )
    return SearchResponse(
        items=result["hits"],
        total=result["total"],
        limit=limit,
        offset=offset,
    )
