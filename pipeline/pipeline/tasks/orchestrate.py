"""배치 진입점 — 소스 수집 → 필터 → AI 처리 → 발행 순서 조율."""
import uuid
from datetime import UTC, datetime

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
    batch_id = f"batch-{datetime.now(UTC).strftime('%Y%m%d')}-{scheduled_hour:02d}h-{uuid.uuid4().hex[:8]}"
    scheduled_at = datetime.now(UTC)

    logger.info(f"[{batch_id}] 배치 시작 (scheduled_hour={scheduled_hour})")

    try:
        batch_log_svc.run_sync(batch_log_svc.create_batch_log(batch_id, scheduled_at))
        batch_log_svc.run_sync(batch_log_svc.mark_batch_running(batch_id))

        result = _run_pipeline(batch_id, scheduled_hour=scheduled_hour)

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

        # 배치 완료 후 소스 상태 점검 트리거
        try:
            from pipeline.tasks.check_source_health import check_and_alert
            check_and_alert.apply_async()
        except Exception as e:
            logger.warning(f"[{batch_id}] 소스 상태 점검 태스크 실행 실패: {e}")

        # 배치 완료 후 푸시 알림 발송
        try:
            from pipeline.tasks.send_push import send_batch_push
            news_cnt = result["published_by_type"].get("NEWS", 0)
            tech_cnt = result["published_by_type"].get("TECHNIQUE", 0)
            send_batch_push.apply_async(kwargs={"news_count": news_cnt, "tech_count": tech_cnt})
        except Exception as e:
            logger.warning(f"[{batch_id}] 푸시 알림 태스크 실행 실패: {e}")

    except Exception as exc:
        logger.error(f"[{batch_id}] 배치 실패: {exc}", exc_info=True)
        try:
            batch_log_svc.run_sync(batch_log_svc.mark_batch_failed(batch_id, str(exc)))
        except Exception:
            pass
        raise self.retry(exc=exc)


def _run_pipeline(batch_id: str, scheduled_hour: int = 0) -> dict:
    """파이프라인 단계 호출 — 수집 → 필터 → AI → 발행."""
    from pipeline.sources.group_a import collect_group_a
    from pipeline.sources.group_b import collect_group_b1
    from pipeline.sources.group_b2 import collect_group_b2
    from pipeline.sources.group_b3 import collect_group_b3
    from pipeline.sources.group_b4 import collect_group_b4
    from pipeline.sources.group_c import collect_group_c1
    from pipeline.sources.group_c2 import collect_group_c2
    from pipeline.sources.group_d import collect_group_d1
    from pipeline.sources.group_d2 import collect_group_d2

    collected_by_group: dict[str, int] = {
        "A": 0, "B1": 0, "B2": 0, "B3": 0, "B4": 0, "C1": 0, "C2": 0, "D1": 0, "D2": 0,
    }
    published_by_type: dict[str, int] = {"NEWS": 0, "TECHNIQUE": 0}
    failed_count = 0
    api_tokens_used = 0
    api_cost_usd = 0.0
    deduplicated_count = 0

    # ① 소스별 수집
    # 데모 모드: 외부 소스를 호출하지 않고 고정 스냅샷에서 수집(오프라인·무비용·결정적).
    from pipeline.ai.demo_client import is_demo_mode
    if is_demo_mode():
        from pipeline.sources.demo_snapshot import collect_demo_snapshot
        raw_items, snapshot_counts = collect_demo_snapshot()
        collected_by_group.update(snapshot_counts)
        total_collected = sum(collected_by_group.values())
        logger.info(f"[{batch_id}] (DEMO) 스냅샷 수집: {collected_by_group} 총 {total_collected}건")
        return _process_items(
            batch_id, raw_items, collected_by_group, deduplicated_count,
            published_by_type, failed_count, api_tokens_used, api_cost_usd,
        )

    try:
        group_a = collect_group_a()
        collected_by_group["A"] = len(group_a)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group A 수집 실패: {exc}", exc_info=True)
        group_a = []
        failed_count += 1

    try:
        group_b1 = collect_group_b1()
        collected_by_group["B1"] = len(group_b1)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group B-1 수집 실패: {exc}", exc_info=True)
        group_b1 = []
        failed_count += 1

    try:
        group_b2 = collect_group_b2(scheduled_hour=scheduled_hour)
        collected_by_group["B2"] = len(group_b2)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group B-2 수집 실패: {exc}", exc_info=True)
        group_b2 = []
        failed_count += 1

    try:
        group_b3 = collect_group_b3()
        collected_by_group["B3"] = len(group_b3)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group B-3 수집 실패: {exc}", exc_info=True)
        group_b3 = []
        failed_count += 1

    try:
        group_b4 = collect_group_b4()
        collected_by_group["B4"] = len(group_b4)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group B-4 수집 실패: {exc}", exc_info=True)
        group_b4 = []
        failed_count += 1

    try:
        group_c1 = collect_group_c1()
        collected_by_group["C1"] = len(group_c1)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group C-1 수집 실패: {exc}", exc_info=True)
        group_c1 = []
        failed_count += 1

    try:
        group_c2 = collect_group_c2()
        collected_by_group["C2"] = len(group_c2)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group C-2 수집 실패: {exc}", exc_info=True)
        group_c2 = []
        failed_count += 1

    try:
        group_d1 = collect_group_d1()
        collected_by_group["D1"] = len(group_d1)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group D-1 수집 실패: {exc}", exc_info=True)
        group_d1 = []
        failed_count += 1

    try:
        group_d2 = collect_group_d2()
        collected_by_group["D2"] = len(group_d2)
    except Exception as exc:
        logger.error(f"[{batch_id}] Group D-2 수집 실패: {exc}", exc_info=True)
        group_d2 = []
        failed_count += 1

    raw_items = group_a + group_b1 + group_b2 + group_b3 + group_b4 + group_c1 + group_c2 + group_d1 + group_d2
    total_collected = sum(collected_by_group.values())
    logger.info(f"[{batch_id}] 수집 완료: {collected_by_group} 총 {total_collected}건")

    return _process_items(
        batch_id, raw_items, collected_by_group, deduplicated_count,
        published_by_type, failed_count, api_tokens_used, api_cost_usd,
    )


def _process_items(
    batch_id: str,
    raw_items: list,
    collected_by_group: dict[str, int],
    deduplicated_count: int,
    published_by_type: dict[str, int],
    failed_count: int,
    api_tokens_used: int,
    api_cost_usd: float,
) -> dict:
    """② 중복 제거 → ③ AI 처리 → 발행 (수집 이후 공통 단계)."""

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

    # 월 예산 하드 캡 — 이번 달 누적 비용이 MONTHLY_BUDGET_USD에 도달하면 AI 처리를 중단한다.
    # (수집·디듀프는 무료이므로 그대로 진행, AI 호출만 차단)
    import os
    monthly_budget = float(os.getenv("MONTHLY_BUDGET_USD", "100.0"))
    try:
        month_spent = batch_log_svc.run_sync(batch_log_svc.get_month_cost_usd())
    except Exception as exc:
        logger.warning(f"[{batch_id}] 월 비용 조회 실패(예산 캡 비활성): {exc}")
        month_spent = 0.0
    budget_remaining = monthly_budget - month_spent
    budget_exhausted = False

    if budget_remaining <= 0:
        logger.warning(
            f"[{batch_id}] 월 예산 소진(${month_spent:.2f}/${monthly_budget:.2f}) — AI 처리 전체 스킵"
        )

    for item in filtered_items:
        if api_cost_usd >= budget_remaining:
            if not budget_exhausted:
                budget_exhausted = True
                logger.warning(
                    f"[{batch_id}] 월 예산 도달 — 남은 {len(filtered_items)}건 중 이후 항목 처리 중단 "
                    f"(이번 배치 ${api_cost_usd:.4f}, 월 누적 ${month_spent + api_cost_usd:.2f}/${monthly_budget:.2f})"
                )
            break
        try:
            is_news = item.source_group in _NEWS_GROUPS

            # P2-6/P2-7: 타입별 AI 처리
            card = process_news(item) if is_news else process_technique(item)
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
                if not passed:
                    logger.info(
                        f"[{batch_id}] 역번역 검증 실패 score={score:.3f} — 검토 큐 보류: {item.url}"
                    )
            else:
                passed, score, back_text = True, 1.0, None

            # 검증 실패 카드도 비공개 초안으로 저장되어 관리자 검토 큐로 들어간다.
            # publish_*는 공개 발행(passed && 신규)일 때만 True를 반환한다.
            if is_news:
                published = publish_news_card(card, batch_id, back_text, score, passed)
                key = "NEWS"
            else:
                published = publish_technique_card(card, batch_id, back_text, score, passed)
                key = "TECHNIQUE"

            if published:
                published_by_type[key] += 1
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
