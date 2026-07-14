#!/usr/bin/env python3
"""
검색 인덱스 생성 + 기존 카드 전체 재인덱싱 스크립트.

실행 (backend/ 디렉터리에서):
    python es/setup.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from opensearchpy import AsyncOpenSearch
from opensearchpy.helpers import async_bulk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.card import Card
from app.services.search import INDEX_NAME, build_card_doc

MAPPINGS_FILE = Path(__file__).parent / "mappings" / "cards.json"


async def main() -> None:
    mapping = json.loads(MAPPINGS_FILE.read_text())
    es = AsyncOpenSearch(hosts=[settings.ELASTICSEARCH_URL])

    try:
        # 1. 인덱스 생성 (기존 인덱스 재생성)
        if await es.indices.exists(index=INDEX_NAME):
            print(f"인덱스 '{INDEX_NAME}' 이미 존재 — 삭제 후 재생성합니다.")
            await es.indices.delete(index=INDEX_NAME)

        await es.indices.create(index=INDEX_NAME, body=mapping)
        print(f"인덱스 '{INDEX_NAME}' 생성 완료.")

        # 2. DB에서 전체 카드 조회
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # 발행된(is_published) 카드만 색인 — 번역 검토 보류 초안은 검색 노출 금지
            result = await session.execute(
                select(Card).options(selectinload(Card.tags)).where(Card.is_published.is_(True))
            )
            cards = result.scalars().all()

        await engine.dispose()
        print(f"카드 {len(cards)}건 인덱싱 시작...")

        # 3. Bulk 인덱싱
        if cards:
            actions = [
                {"_index": INDEX_NAME, "_id": str(c.id), **build_card_doc(c)} for c in cards
            ]
            success, errors = await async_bulk(es, actions, raise_on_error=False)
            print(f"성공: {success}건 / 오류: {len(errors)}건")
        else:
            print("인덱싱할 카드가 없습니다.")

    finally:
        await es.close()
        print("완료.")


if __name__ == "__main__":
    asyncio.run(main())
