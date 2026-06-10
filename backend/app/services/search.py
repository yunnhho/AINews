"""Elasticsearch 쿼리 래퍼 + 인덱스 설정."""
import json
from pathlib import Path

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.config import settings

INDEX_NAME = "cards"

# 인덱스 매핑의 단일 출처는 es/mappings/cards.json (es/setup.py 재색인 스크립트와 공유)
_MAPPINGS_FILE = Path(__file__).resolve().parent.parent.parent / "es" / "mappings" / "cards.json"
_MAPPING = json.loads(_MAPPINGS_FILE.read_text())


def _client() -> AsyncElasticsearch:
    return AsyncElasticsearch(settings.ELASTICSEARCH_URL)


async def setup_index() -> None:
    """앱 시작 시 인덱스 초기화 (멱등)."""
    es = _client()
    try:
        exists = await es.indices.exists(index=INDEX_NAME)
        if not exists:
            await es.indices.create(
                index=INDEX_NAME,
                settings=_MAPPING["settings"],
                mappings=_MAPPING["mappings"],
            )
    finally:
        await es.close()


async def search_cards(
    q: str,
    category: str | None = None,
    card_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db=None,
    current_user=None,
) -> dict:
    filters: list[dict] = []
    if category:
        filters.append({"term": {"category": category}})
    if card_type:
        filters.append({"term": {"card_type": card_type}})

    es = _client()
    try:
        result = await es.search(
            index=INDEX_NAME,
            query={
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": q,
                                # 한국어(nori) + 영어(english) 서브필드 + 태그(키워드) 동시 검색
                                "fields": [
                                    "title^3", "title.en^3",
                                    "summary^2", "summary.en^2",
                                    "problem", "problem.en",
                                    "idea", "idea.en",
                                    "tags.text^2",
                                ],
                                "type": "best_fields",
                                "operator": "or",
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
            # 관련도 우선, 동점이면 최신순
            sort=["_score", {"published_at": "desc"}],
            from_=offset,
            size=limit,
        )
    finally:
        await es.close()

    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"]
    ordered_ids = [int(h["_id"]) for h in hits]

    # ES는 매칭 ID만 사용하고, 응답 카드는 DB에서 조회해 피드와 동일한 형태로 직렬화한다.
    # (ES _source는 태그가 문자열이고 is_liked 등이 없어 프론트 Card 형태와 불일치)
    items = await _hydrate_cards_from_db(ordered_ids, db, current_user)
    return {"hits": items, "total": total}


async def _hydrate_cards_from_db(ordered_ids: list[int], db, current_user) -> list[dict]:
    """ES 매칭 ID를 DB에서 조회해 피드와 동일한 직렬화 형태(dict)로 반환. ES 정렬 순서 유지."""
    if db is None or not ordered_ids:
        return []

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.card import Card
    from app.services.cards import _get_user_interaction_ids, _serialize_card

    result = await db.execute(
        select(Card)
        .options(selectinload(Card.tags))
        .where(Card.id.in_(ordered_ids), Card.is_published.is_(True))
    )
    cards = {c.id: c for c in result.scalars()}

    liked_ids: set[int] = set()
    bookmarked_ids: set[int] = set()
    if current_user:
        liked_ids, bookmarked_ids = await _get_user_interaction_ids(db, current_user.id)

    # ES 정렬 순서를 유지하며 직렬화
    return [
        _serialize_card(cards[cid], liked_ids, bookmarked_ids)
        for cid in ordered_ids
        if cid in cards
    ]


async def index_card(doc: dict) -> None:
    """카드 문서 1건을 Elasticsearch에 색인."""
    es = _client()
    try:
        await es.index(index=INDEX_NAME, id=str(doc["id"]), document=doc)
    finally:
        await es.close()


async def delete_card(card_id: int) -> None:
    es = _client()
    try:
        await es.delete(index=INDEX_NAME, id=str(card_id))
    except NotFoundError:
        pass
    finally:
        await es.close()
