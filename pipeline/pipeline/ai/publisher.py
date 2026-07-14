"""카드 DB 저장 + 검색 색인.

orchestrate.py 호출 시그니처:
  publish_news_card(card, batch_id, back_text, score, passed) -> bool
  publish_technique_card(card, batch_id, back_text, score, passed) -> bool

역번역 검증을 통과한(passed=True) 카드만 is_published=True로 공개 발행하고
검색 인덱스에 색인한다. 실패한(passed=False) 영어 원본 카드는 is_published=False
초안으로 저장되고 TranslationLog가 기록되어 관리자 번역 검토 큐로 들어간다.
반환값은 "공개 발행 여부"(passed && 신규)이며, 초안 저장·중복은 False.
"""
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pipeline.db import SessionLocal as _Session
from pipeline.db import run_sync as _run


async def _get_or_create_tags(session: AsyncSession, tag_slugs: list[str]) -> list:
    from app.models.card import Tag

    tags = []
    for slug in tag_slugs:
        result = await session.execute(select(Tag).where(Tag.slug == slug))
        tag = result.scalar_one_or_none()
        if tag is None:
            tag = Tag(name=slug.replace("-", " "), slug=slug)
            session.add(tag)
            await session.flush()
        tags.append(tag)
    return tags


def _enum_or(enum_cls, value, default):
    try:
        return enum_cls(value)
    except ValueError:
        return default


async def _index(card) -> None:
    """검색 색인 (실패해도 DB 롤백 없음). 백엔드와 동일한 opensearch-py 클라이언트 사용."""
    try:
        from app.services.search import build_card_doc, index_card
        await index_card(build_card_doc(card))
    except Exception:
        pass


async def _save_card(
    card_data,
    card_type,
    type_fields: dict,
    batch_id: str,
    back_text: str | None,
    score: float,
    passed: bool,
) -> bool:
    from app.models.batch import TranslationLog
    from app.models.card import Card, Category, Difficulty, OriginalLang
    from app.models.card import SourceGroup as CardSG

    async with _Session() as session:
        try:
            existing = await session.execute(
                select(Card.id).where(Card.source_url == card_data.source_url)
            )
            if existing.scalar_one_or_none() is not None:
                return False

            tags = await _get_or_create_tags(session, card_data.tags)
            published_at = card_data.published_at
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=UTC)

            card = Card(
                card_type=card_type,
                title=card_data.title,
                summary=card_data.summary,
                source_url=card_data.source_url,
                source_name=card_data.source_name,
                source_group=_enum_or(CardSG, card_data.source_group, CardSG.NEWS_RSS),
                original_lang=_enum_or(OriginalLang, card_data.original_lang.upper(), OriginalLang.EN),
                category=Category(card_data.category),
                difficulty=Difficulty(card_data.difficulty),
                is_published=passed,
                batch_id=batch_id,
                published_at=published_at,
                tags=tags,
                **type_fields,
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
            await _index(result.scalar_one())
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
    from app.models.card import CardType

    return _run(_save_card(
        card_data, CardType.NEWS,
        {"key_points": card_data.key_points},
        batch_id, back_text, score, passed,
    ))


def publish_technique_card(
    card_data,
    batch_id: str,
    back_text: str | None,
    score: float,
    passed: bool,
) -> bool:
    from app.models.card import CardType

    return _run(_save_card(
        card_data, CardType.TECHNIQUE,
        {
            "problem": card_data.problem,
            "idea": card_data.idea,
            "code_snippet": card_data.code_snippet,
            "caveats": card_data.caveats or None,
            "prerequisites": card_data.prerequisites,
        },
        batch_id, back_text, score, passed,
    ))
