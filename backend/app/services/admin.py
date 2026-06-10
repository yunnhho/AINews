from datetime import UTC, datetime, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.exceptions import NotFoundError
from app.models.batch import BatchLog, BatchStatus, SourceHealth, TranslationLog
from app.models.card import Card, CardType
from app.services import search as search_svc


async def get_metrics(db: AsyncSession) -> dict:
    today = datetime.now(UTC).date()
    week_ago = datetime.now(UTC) - timedelta(days=7)
    month_start = today.replace(day=1)
    thirty_days_ago = today - timedelta(days=30)

    # 오늘 발행수 by type
    rows = (await db.execute(
        select(Card.card_type, func.count().label("cnt"))
        .where(cast(Card.published_at, Date) == today)
        .group_by(Card.card_type)
    )).all()
    today_published = {r.card_type.value: r.cnt for r in rows}

    # 7일 배치 성공률
    row = (await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(BatchLog.status == BatchStatus.COMPLETED).label("success"),
        ).where(BatchLog.scheduled_at >= week_ago)
    )).one()
    batch_success_rate = (row.success / row.total) if row.total > 0 else 0.0

    # 번역 통과율 (최근 100건)
    recent_passed = (await db.execute(
        select(TranslationLog.passed)
        .order_by(TranslationLog.created_at.desc())
        .limit(100)
    )).scalars().all()
    translation_pass_rate = (sum(1 for p in recent_passed if p) / len(recent_passed)) if recent_passed else 0.0

    # 이달 API 비용
    monthly_cost = float((await db.execute(
        select(func.coalesce(func.sum(BatchLog.api_cost_usd), 0))
        .where(cast(BatchLog.scheduled_at, Date) >= month_start)
    )).scalar_one())

    # 경보 소스 (consecutive_failures >= 1)
    alert_sources = (await db.execute(
        select(SourceHealth)
        .where(SourceHealth.consecutive_failures >= 1)
        .order_by(SourceHealth.consecutive_failures.desc())
    )).scalars().all()

    # 일별 비용 (최근 30일)
    daily_rows = (await db.execute(
        select(
            cast(BatchLog.scheduled_at, Date).label("day"),
            func.sum(BatchLog.api_cost_usd).label("cost_usd"),
        )
        .where(cast(BatchLog.scheduled_at, Date) >= thirty_days_ago)
        .group_by(cast(BatchLog.scheduled_at, Date))
        .order_by(cast(BatchLog.scheduled_at, Date))
    )).all()

    return {
        "today_published": today_published,
        "batch_success_rate_7d": round(batch_success_rate, 4),
        "translation_pass_rate": round(translation_pass_rate, 4),
        "monthly_api_cost_usd": monthly_cost,
        "monthly_budget_usd": settings.MONTHLY_BUDGET_USD,
        "alert_sources": [_source_health_dict(s) for s in alert_sources],
        "daily_costs": [{"date": str(r.day), "cost_usd": float(r.cost_usd)} for r in daily_rows],
    }


async def get_batches(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(BatchLog).order_by(BatchLog.scheduled_at.desc()).limit(50)
    )).scalars().all()
    return {"items": [_batch_log_dict(b) for b in rows]}


async def get_sources_health(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(SourceHealth).order_by(SourceHealth.consecutive_failures.desc())
    )).scalars().all()
    return {"items": [_source_health_dict(s) for s in rows]}


async def toggle_source(db: AsyncSession, source_id: int, enabled: bool) -> dict:
    health = (await db.execute(
        select(SourceHealth).where(SourceHealth.source_id == source_id)
    )).scalar_one_or_none()
    if health is None:
        raise NotFoundError("source")
    health.enabled = enabled
    await db.commit()
    return _source_health_dict(health)


async def get_translation_queue(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(TranslationLog)
        .where(TranslationLog.passed == False)  # noqa: E712
        .order_by(TranslationLog.created_at.desc())
    )).scalars().all()
    return {"items": [_translation_log_dict(t) for t in rows]}


async def handle_translation_review(db: AsyncSession, log_id: int, action: str) -> dict:
    tlog = (await db.execute(
        select(TranslationLog).where(TranslationLog.id == log_id)
    )).scalar_one_or_none()
    if tlog is None:
        raise NotFoundError("translation_log")

    if action == "approve":
        tlog.passed = True
        # 검토 승인 → 카드를 공개 발행하고 검색 색인에 반영
        card = (await db.execute(
            select(Card).options(selectinload(Card.tags)).where(Card.id == tlog.card_id)
        )).scalar_one_or_none()
        if card is not None:
            card.is_published = True
        await db.commit()
        if card is not None:
            try:
                await search_svc.index_card(_card_to_es_doc(card))
            except Exception:
                pass  # 색인 실패해도 발행 자체는 유지
        return {"status": "approved", "id": log_id}

    # action == "reject": 연관 카드 삭제 (DB CASCADE로 translation_log도 삭제됨)
    card = (await db.execute(
        select(Card).where(Card.id == tlog.card_id)
    )).scalar_one_or_none()
    card_id = card.id if card else None
    if card:
        await db.delete(card)
    await db.commit()
    if card_id is not None:
        try:
            await search_svc.delete_card(card_id)
        except Exception:
            pass
    return {"status": "rejected", "id": log_id}


async def get_daily_costs(db: AsyncSession) -> dict:
    today = datetime.now(UTC).date()
    thirty_days_ago = today - timedelta(days=30)
    rows = (await db.execute(
        select(
            cast(BatchLog.scheduled_at, Date).label("day"),
            func.sum(BatchLog.api_cost_usd).label("cost_usd"),
            func.sum(BatchLog.api_tokens_used).label("tokens"),
        )
        .where(cast(BatchLog.scheduled_at, Date) >= thirty_days_ago)
        .group_by(cast(BatchLog.scheduled_at, Date))
        .order_by(cast(BatchLog.scheduled_at, Date))
    )).all()
    return {
        "items": [
            {"date": str(r.day), "cost_usd": float(r.cost_usd), "tokens": int(r.tokens)}
            for r in rows
        ]
    }


def _card_to_es_doc(card: Card) -> dict:
    """Card ORM → Elasticsearch 문서 (publisher._build_es_doc와 동일 스키마)."""
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
        "tags": [t.name for t in (card.tags or [])],
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


def _batch_log_dict(b: BatchLog) -> dict:
    return {
        "id": b.id,
        "batch_id": b.batch_id,
        "scheduled_at": b.scheduled_at.isoformat(),
        "started_at": b.started_at.isoformat() if b.started_at else None,
        "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        "status": b.status.value,
        "collected_by_group": b.collected_by_group,
        "deduplicated_count": b.deduplicated_count,
        "published_by_type": b.published_by_type,
        "failed_count": b.failed_count,
        "api_tokens_used": b.api_tokens_used,
        "api_cost_usd": float(b.api_cost_usd),
        "error_log": b.error_log,
    }


def _source_health_dict(s: SourceHealth) -> dict:
    return {
        "source_id": s.source_id,
        "source_name": s.source_name,
        "source_group": s.source_group,
        "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
        "consecutive_failures": s.consecutive_failures,
        "last_error_log": s.last_error_log,
        "enabled": s.enabled,
        "status": "critical" if s.consecutive_failures >= 3 else "warning",
    }


def _translation_log_dict(t: TranslationLog) -> dict:
    return {
        "id": t.id,
        "card_id": t.card_id,
        "original_text": t.original_text,
        "translated_text": t.translated_text,
        "back_translated_text": t.back_translated_text,
        "similarity_score": t.similarity_score,
        "passed": t.passed,
        "retry_count": t.retry_count,
        "created_at": t.created_at.isoformat(),
    }
