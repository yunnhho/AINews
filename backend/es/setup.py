#!/usr/bin/env python3
"""
Elasticsearch 인덱스 생성 + 기존 카드 전체 재인덱싱 스크립트.

실행 (backend/ 디렉터리에서):
    python es/setup.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.card import Card, CardType

INDEX_NAME = "cards"
MAPPINGS_FILE = Path(__file__).parent / "mappings" / "cards.json"


def _build_action(card: Card) -> dict:
    tags = [t.name for t in (card.tags or [])]
    doc: dict = {
        "_index": INDEX_NAME,
        "_id": str(card.id),
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


async def main() -> None:
    mapping = json.loads(MAPPINGS_FILE.read_text())
    es = AsyncElasticsearch(settings.ELASTICSEARCH_URL)

    try:
        # 1. 인덱스 생성 (기존 인덱스 재생성)
        exists = await es.indices.exists(index=INDEX_NAME)
        if exists:
            print(f"인덱스 '{INDEX_NAME}' 이미 존재 — 삭제 후 재생성합니다.")
            await es.indices.delete(index=INDEX_NAME)

        await es.indices.create(
            index=INDEX_NAME,
            settings=mapping["settings"],
            mappings=mapping["mappings"],
        )
        print(f"인덱스 '{INDEX_NAME}' 생성 완료.")

        # 2. DB에서 전체 카드 조회
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await session.execute(select(Card))
            cards = result.scalars().all()

        await engine.dispose()
        print(f"카드 {len(cards)}건 인덱싱 시작...")

        # 3. Bulk 인덱싱
        if cards:
            actions = [_build_action(c) for c in cards]
            success, errors = await async_bulk(es, actions, raise_on_error=False)
            print(f"성공: {success}건 / 오류: {len(errors)}건")
        else:
            print("인덱싱할 카드가 없습니다.")

    finally:
        await es.close()
        print("완료.")


if __name__ == "__main__":
    asyncio.run(main())
