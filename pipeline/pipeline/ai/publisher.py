"""카드 DB 저장 + Elasticsearch 인덱싱.

orchestrate.py 호출 시그니처:
  publish_news_card(card, batch_id, back_text, score, passed) -> bool
  publish_technique_card(card, batch_id, back_text, score, passed) -> bool

역번역 검증을 통과한(passed=True) 카드만 is_published=True로 공개 발행하고
Elasticsearch에 색인한다. 실패한(passed=False) 영어 원본 카드는 is_published=False
초안으로 저장되고 TranslationLog가 기록되어 관리자 번역 검토 큐로 들어간다.
반환값은 "공개 발행 여부"(passed && 신규)이며, 초안 저장·중복은 False.
"""
import asyncio
import os
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse")
# _run()이 카드마다 새 이벤트 루프를 생성하므로 NullPool로 커넥션 재사용을 막는다.
_engine = create_async_engine(_DATABASE_URL, poolclass=NullPool)
_Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _get_or_create_tags(session: AsyncSession, tag_slugs: list[str]) -> list:
    from app.models.card import Tag

    tags = []
    for slug in tag_slugs:
        name = slug.replace("-", " ")
        result = await session.execute(select(Tag).where(Tag.slug == slug))
        tag = result.scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name, slug=slug)
            session.add(tag)
            await session.flush()
        tags.append(tag)
    return tags


def _to_card_source_group(sg_value: str):
    from app.models.card import SourceGroup as CardSG
    mapping = {
        "NEWS_RSS": CardSG.NEWS_RSS,
        "GITHUB": CardSG.GITHUB,
        "ENG_BLOG": CardSG.ENG_BLOG,
        "NEWSLETTER": CardSG.NEWSLETTER,
    }
    return mapping.get(sg_value, CardSG.NEWS_RSS)


def _to_original_lang(lang: str):
    from app.models.card import OriginalLang
    mapping = {"KO": OriginalLang.KO, "EN": OriginalLang.EN, "JA": OriginalLang.JA, "ZH": OriginalLang.ZH}
    return mapping.get(lang.upper(), OriginalLang.EN)


def _build_es_doc(card) -> dict:
    """Card ORM → Elasticsearch 문서."""
    from app.models.card import CardType
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


async def _index(card) -> None:
    """Elasticsearch 인덱싱 (실패해도 DB 롤백 없음)."""
    try:
        from elasticsearch import AsyncElasticsearch
        url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
        doc = _build_es_doc(card)
        es = AsyncElasticsearch(url)
        try:
            await es.index(index="cards", id=str(card.id), document=doc)
        finally:
            await es.close()
    except Exception:
        pass


async def _save_news(
    card_data,
    batch_id: str,
    back_text: str | None,
    score: float,
    passed: bool,
) -> bool:
    from app.models.batch import TranslationLog
    from app.models.card import Card, CardType, Category, Difficulty

    async with _Session() as session:
        try:
            existing = await session.execute(select(Card.id).where(Card.source_url == card_data.source_url))
            if existing.scalar_one_or_none() is not None:
                return False

            tags = await _get_or_create_tags(session, card_data.tags)
            published_at = card_data.published_at
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=UTC)

            card = Card(
                card_type=CardType.NEWS,
                title=card_data.title,
                summary=card_data.summary,
                key_points=card_data.key_points,
                source_url=card_data.source_url,
                source_name=card_data.source_name,
                source_group=_to_card_source_group(card_data.source_group),
                original_lang=_to_original_lang(card_data.original_lang),
                category=Category(card_data.category),
                difficulty=Difficulty(card_data.difficulty),
                is_published=passed,
                batch_id=batch_id,
                published_at=published_at,
                tags=tags,
            )
            session.add(card)
            await session.flush()

            if card_data.original_lang.upper() == "EN":
                session.add(TranslationLog(
                    card_id=card.id,
                    original_text=(card_data.source_name + "\n" + card_data.title)[:2000],
                    translated_text=card_data.summary,
                    back_translated_text=back_text,
                    similarity_score=score,
                    passed=passed,
                ))

            await session.commit()

            if not passed:
                return False  # 비공개 초안 — 색인하지 않음

            result = await session.execute(
                select(Card).options(selectinload(Card.tags)).where(Card.id == card.id)
            )
            loaded = result.scalar_one()
            await _index(loaded)
            return True

        except Exception:
            await session.rollback()
            return False


async def _save_technique(
    card_data,
    batch_id: str,
    back_text: str | None,
    score: float,
    passed: bool,
) -> bool:
    from app.models.batch import TranslationLog
    from app.models.card import Card, CardType, Category, Difficulty

    async with _Session() as session:
        try:
            existing = await session.execute(select(Card.id).where(Card.source_url == card_data.source_url))
            if existing.scalar_one_or_none() is not None:
                return False

            tags = await _get_or_create_tags(session, card_data.tags)
            published_at = card_data.published_at
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=UTC)

            card = Card(
                card_type=CardType.TECHNIQUE,
                title=card_data.title,
                summary=card_data.summary,
                problem=card_data.problem,
                idea=card_data.idea,
                code_snippet=card_data.code_snippet,
                caveats=card_data.caveats if card_data.caveats else None,
                prerequisites=card_data.prerequisites,
                source_url=card_data.source_url,
                source_name=card_data.source_name,
                source_group=_to_card_source_group(card_data.source_group),
                original_lang=_to_original_lang(card_data.original_lang),
                category=Category(card_data.category),
                difficulty=Difficulty(card_data.difficulty),
                is_published=passed,
                batch_id=batch_id,
                published_at=published_at,
                tags=tags,
            )
            session.add(card)
            await session.flush()

            if card_data.original_lang.upper() == "EN":
                session.add(TranslationLog(
                    card_id=card.id,
                    original_text=(card_data.source_name + "\n" + card_data.title)[:2000],
                    translated_text=card_data.summary,
                    back_translated_text=back_text,
                    similarity_score=score,
                    passed=passed,
                ))

            await session.commit()

            if not passed:
                return False  # 비공개 초안 — 색인하지 않음

            result = await session.execute(
                select(Card).options(selectinload(Card.tags)).where(Card.id == card.id)
            )
            loaded = result.scalar_one()
            await _index(loaded)
            return True

        except Exception:
            await session.rollback()
            return False


# ── 공개 인터페이스 (orchestrate.py 호출 시그니처와 일치) ──────────────

def publish_news_card(
    card_data,
    batch_id: str,
    back_text: str | None,
    score: float,
    passed: bool,
) -> bool:
    return _run(_save_news(card_data, batch_id, back_text, score, passed))


def publish_technique_card(
    card_data,
    batch_id: str,
    back_text: str | None,
    score: float,
    passed: bool,
) -> bool:
    return _run(_save_technique(card_data, batch_id, back_text, score, passed))
