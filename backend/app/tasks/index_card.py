"""카드 저장 시 Elasticsearch 인덱스 동기화."""
from app.models.card import Card, CardType
from app.services import search as search_svc


def _build_doc(card: Card) -> dict:
    """Card ORM 객체 → Elasticsearch 문서."""
    tags = [t.name for t in (card.tags or [])]
    doc: dict = {
        "id": card.id,
        "card_type": card.card_type.value,
        "category": card.category.value,
        "difficulty": card.difficulty.value,
        "title": card.title,
        "summary": card.summary,
        "source_url": card.source_url,
        "source_name": card.source_name,
        "like_count": card.like_count,
        "published_at": card.published_at.isoformat(),
        "tags": tags,
    }
    if card.card_type == CardType.NEWS:
        doc["key_points"] = card.key_points or []
    else:
        doc.update(
            problem=card.problem,
            idea=card.idea,
            code_snippet=card.code_snippet,
            caveats=card.caveats or [],
            prerequisites=card.prerequisites,
        )
    return doc


async def sync_card_to_index(card: Card) -> None:
    """카드를 Elasticsearch에 색인 (저장 후 이벤트 훅으로 호출)."""
    doc = _build_doc(card)
    await search_svc.index_card(doc)
