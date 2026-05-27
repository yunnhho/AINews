"""Meilisearch 쿼리 래퍼 + 인덱스 설정."""
from meilisearch_python_sdk import AsyncClient

from app.config import settings

INDEX_NAME = "cards"
_SEARCHABLE = ["title", "summary", "problem", "idea", "tags_str"]
_FILTERABLE = ["category", "card_type", "difficulty"]
_SORTABLE = ["published_at_ts", "like_count"]


def _client() -> AsyncClient:
    return AsyncClient(settings.MEILISEARCH_URL, settings.MEILISEARCH_MASTER_KEY)


async def setup_index() -> None:
    """앱 시작 시 인덱스·속성 초기화 (멱등)."""
    async with _client() as client:
        try:
            await client.create_index(INDEX_NAME, primary_key="id")
        except Exception:
            pass  # 이미 존재하면 무시
        index = client.index(INDEX_NAME)
        await index.update_searchable_attributes(_SEARCHABLE)
        await index.update_filterable_attributes(_FILTERABLE)
        await index.update_sortable_attributes(_SORTABLE)


async def search_cards(
    q: str,
    category: str | None = None,
    card_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    filters: list[str] = []
    if category:
        filters.append(f'category = "{category}"')
    if card_type:
        filters.append(f'card_type = "{card_type}"')

    filter_str = " AND ".join(filters) if filters else None

    async with _client() as client:
        index = client.index(INDEX_NAME)
        result = await index.search(
            q,
            limit=limit,
            offset=offset,
            filter=filter_str,
            sort=["published_at_ts:desc"],
        )

    return {
        "hits": result.hits,
        "total": result.estimated_total_hits or 0,
    }


async def index_card(doc: dict) -> None:
    """카드 문서 1건을 Meilisearch에 색인."""
    async with _client() as client:
        index = client.index(INDEX_NAME)
        await index.add_documents([doc])


async def delete_card(card_id: int) -> None:
    async with _client() as client:
        index = client.index(INDEX_NAME)
        await index.delete_document(str(card_id))
