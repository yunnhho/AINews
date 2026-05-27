"""배치 진입점 — 소스 수집 → 필터 → AI 처리 → 발행 순서 조율."""
import uuid
from datetime import datetime, timezone

from celery import shared_task
from celery.utils.log import get_task_logger

from pipeline.celery_app import app
from pipeline.models import batch_log as batch_log_svc

logger = get_task_logger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 60 * 15  # 15분


@app.task(
    bind=True,
    name="pipeline.tasks.orchestrate.run_batch",
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_DELAY,
    queue="batch",
)
def run_batch(self, scheduled_hour: int = 0):
    """KST 00/06/12/18시 배치 진입점."""
    batch_id = f"batch-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{scheduled_hour:02d}h-{uuid.uuid4().hex[:8]}"
    scheduled_at = datetime.now(timezone.utc)

    logger.info(f"[{batch_id}] 배치 시작 (scheduled_hour={scheduled_hour})")

    try:
        batch_log_svc.run_sync(batch_log_svc.create_batch_log(batch_id, scheduled_at))
        batch_log_svc.run_sync(batch_log_svc.mark_batch_running(batch_id))

        result = _run_pipeline(batch_id)

        batch_log_svc.run_sync(
            batch_log_svc.mark_batch_completed(
                batch_id,
                collected_by_group=result["collected_by_group"],
                deduplicated_count=result["deduplicated_count"],
                published_by_type=result["published_by_type"],
                failed_count=result["failed_count"],
                api_tokens_used=result["api_tokens_used"],
                api_cost_usd=result["api_cost_usd"],
            )
        )
        logger.info(f"[{batch_id}] 배치 완료: {result}")

    except Exception as exc:
        logger.error(f"[{batch_id}] 배치 실패: {exc}", exc_info=True)
        try:
            batch_log_svc.run_sync(batch_log_svc.mark_batch_failed(batch_id, str(exc)))
        except Exception:
            pass
        raise self.retry(exc=exc)


def _run_pipeline(batch_id: str) -> dict:
    """파이프라인 단계 호출 — 수집 → 필터 → AI → 발행."""
    from pipeline.sources.group_a import collect_group_a
    from pipeline.sources.group_b import collect_group_b1
    from pipeline.sources.group_c import collect_group_c1
    from pipeline.sources.group_d import collect_group_d1

    collected_by_group: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}
    published_by_type: dict[str, int] = {"NEWS": 0, "TECHNIQUE": 0}
    failed_count = 0
    api_tokens_used = 0
    api_cost_usd = 0.0
    deduplicated_count = 0

    # ① 소스별 수집
    try:
        group_a = collect_group_a()
        collected_by_group["A"] = len(group_a)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group A 수집 실패: {exc}", exc_info=True)
        group_a = []
        failed_count += 1

    try:
        group_b = collect_group_b1()
        collected_by_group["B"] = len(group_b)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group B-1 수집 실패: {exc}", exc_info=True)
        group_b = []
        failed_count += 1

    try:
        group_c = collect_group_c1()
        collected_by_group["C"] = len(group_c)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group C-1 수집 실패: {exc}", exc_info=True)
        group_c = []
        failed_count += 1

    try:
        group_d = collect_group_d1()
        collected_by_group["D"] = len(group_d)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group D-1 수집 실패: {exc}", exc_info=True)
        group_d = []
        failed_count += 1

    raw_items = group_a + group_b + group_c + group_d
    logger.info(f"[{batch_id}] 수집 완료: {collected_by_group} 총 {len(raw_items)}건")

    # ② 중복 필터링 (P2-5)
    from pipeline.filters.dedup import dedup
    filtered_items, dedup_cnt = dedup(raw_items)
    deduplicated_count = dedup_cnt
    logger.info(f"[{batch_id}] 중복 제거: {dedup_cnt}건 → {len(filtered_items)}건 남음")

    # ③ AI 처리 + 발행 (P2-6 ~ P2-7)
    from pipeline.adapters.base import SourceGroup as SGroup
    from pipeline.ai.backtranslate import verify_translation
    from pipeline.ai.news_processor import process_news
    from pipeline.ai.publisher import publish_news_card, publish_technique_card
    from pipeline.ai.technique_processor import process_technique

    # 소스 그룹 → 카드 타입 매핑: NEWS_RSS/NEWSLETTER → NEWS, GITHUB/ENG_BLOG → TECHNIQUE
    _NEWS_GROUPS = {SGroup.NEWS_RSS, SGroup.NEWSLETTER}

    # claude-haiku-4-5-20251001 비용: input $0.80/1M, output $4.00/1M
    _COST_IN = 0.80 / 1_000_000
    _COST_OUT = 4.00 / 1_000_000

    for item in filtered_items:
        try:
            if item.source_group in _NEWS_GROUPS:
                # P2-6: NEWS 처리
                card = process_news(item)
                if card is None:
                    failed_count += 1
                    continue
                api_tokens_used += card.input_tokens + card.output_tokens
                api_cost_usd += card.input_tokens * _COST_IN + card.output_tokens * _COST_OUT

                if publish_news_card(card, batch_id):
                    published_by_type["NEWS"] += 1
                else:
                    failed_count += 1

            else:
                # P2-7: TECHNIQUE 처리
                card = process_technique(item)
                if card is None:
                    failed_count += 1
                    continue
                api_tokens_used += card.input_tokens + card.output_tokens
                api_cost_usd += card.input_tokens * _COST_IN + card.output_tokens * _COST_OUT

                # 역번역 검증 (영어 원본만; 한국어 원본은 번역 없음)
                if item.original_lang == "en":
                    original_ref = item.title + ". " + item.content[:500]
                    passed, score, back_text, bt_in, bt_out = verify_translation(
                        original_ref, card.summary
                    )
                    api_tokens_used += bt_in + bt_out
                    api_cost_usd += bt_in * _COST_IN + bt_out * _COST_OUT
                else:
                    passed, score, back_text = True, 1.0, None

                if not passed:
                    logger.info(
                        f"[{batch_id}] 역번역 검증 실패 score={score:.3f}: {item.url}"
                    )
                    failed_count += 1
                    continue

                if publish_technique_card(card, batch_id, back_text, score, passed):
                    published_by_type["TECHNIQUE"] += 1
                else:
                    failed_count += 1

        except Exception as exc:
            logger.error(f"[{batch_id}] AI 처리 중 예외 {item.url}: {exc}", exc_info=True)
            failed_count += 1

    return {
        "collected_by_group": collected_by_group,
        "deduplicated_count": deduplicated_count,
        "published_by_type": published_by_type,
        "failed_count": failed_count,
        "api_tokens_used": api_tokens_used,
        "api_cost_usd": api_cost_usd,
    }
