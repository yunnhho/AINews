"""Elasticsearch 쿼리 래퍼 + 인덱스 설정."""
from elasticsearch import AsyncElasticsearch, NotFoundError

from app.config import settings

INDEX_NAME = "cards"

_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "korean": {
                    "type": "custom",
                    "tokenizer": "nori_tokenizer",
                    "filter": ["nori_part_of_speech"],
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "title":        {"type": "text", "analyzer": "korean"},
            "summary":      {"type": "text", "analyzer": "korean"},
            "problem":      {"type": "text", "analyzer": "korean"},
            "idea":         {"type": "text", "analyzer": "korean"},
            "tags":         {"type": "keyword"},
            "category":     {"type": "keyword"},
            "card_type":    {"type": "keyword"},
            "difficulty":   {"type": "keyword"},
            "published_at": {"type": "date"},
            "like_count":   {"type": "integer"},
        }
    },
}


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
                                "fields": ["title^3", "summary^2", "problem", "idea"],
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
            sort=[{"published_at": "desc"}],
            from_=offset,
            size=limit,
        )
    finally:
        await es.close()

    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"]
    return {
        "hits": [h["_source"] for h in hits],
        "total": total,
    }


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
