"""소스 그룹 공통 수집 루프 — disabled 체크 → 병렬 fetch(타임아웃) → health 기록."""
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import UTC, datetime, timedelta

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

WINDOW_HOURS = 6.5  # 수집 윈도우 (직전 배치 + 여유 30분)

# 한 소스가 지연돼도 배치 전체가 무한정 늘어지지 않도록 경계를 둔다.
_SOURCE_TIMEOUT = float(os.getenv("SOURCE_FETCH_TIMEOUT", "30"))       # 소스 1개 최대 대기(초)
_PHASE_DEADLINE = float(os.getenv("SOURCE_FETCH_DEADLINE", "120"))     # 수집 단계 전체 상한(초)
_CONCURRENCY = int(os.getenv("SOURCE_FETCH_CONCURRENCY", "8"))         # 동시 fetch 수(소스 예의 상한)


def collect_sources(
    label: str,
    health_group: str,
    fetchers: list[tuple[str, Callable[[datetime], list[RawItem]]]],
    disable_on_404: bool = False,
) -> list[RawItem]:
    """(source_name, fetch(since)) 목록을 **병렬** 수집. 실패·지연은 소스 단위로 격리하고 health에 기록.

    - 네트워크 fetch만 스레드풀에서 병렬 실행하고, health(DB) 기록은 메인 스레드에서 단일 처리한다.
    - 소스별 `_SOURCE_TIMEOUT`, 단계 전체 `_PHASE_DEADLINE`을 넘기면 해당 소스는 실패로 격리한다
      (타임아웃된 fetch 스레드는 데몬으로 남아 소켓 타임아웃에 의해 자연 종료된다).
    - disable_on_404=True면 fetch가 던진 ValueError(GitHub 어댑터의 404)로 소스를 자동 비활성화한다.
    """
    since = datetime.now(UTC) - timedelta(hours=WINDOW_HOURS)
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())

    active = [(name, fetch) for name, fetch in fetchers if name not in disabled]
    for name, _ in fetchers:
        if name in disabled:
            logger.info("[%s] %s: 비활성화됨 — 스킵", label, name)
    if not active:
        logger.info("[%s] 수집 완료: 총 0건", label)
        return []

    all_items: list[RawItem] = []

    def _record_failure(name: str, exc: Exception, *, on_404: bool = False) -> None:
        tag = "404" if on_404 else "실패"
        logger.warning("[%s] %s %s: %s", label, name, tag, exc)
        health_svc.run_sync(
            health_svc.record_failure(name, health_group, str(exc), disable_on_404=on_404)
        )

    # fetch만 병렬화. 결과 처리(health 기록·집계)는 메인 스레드에서 순차 처리한다.
    # with 블록은 종료 시 wait=True로 hung 스레드를 기다려 타임아웃을 무력화하므로 쓰지 않고,
    # shutdown(wait=False, cancel_futures=True)로 미시작분만 취소하고 지연 소스는 방치한다.
    pool = ThreadPoolExecutor(max_workers=max(1, min(_CONCURRENCY, len(active))))
    try:
        future_to_name = {pool.submit(fetch, since): name for name, fetch in active}
        deadline = time.monotonic() + _PHASE_DEADLINE

        for future, name in future_to_name.items():
            remaining = deadline - time.monotonic()
            per_timeout = min(_SOURCE_TIMEOUT, remaining) if remaining > 0 else 0.0
            try:
                items = future.result(timeout=max(0.0, per_timeout))
                all_items.extend(items)
                health_svc.run_sync(health_svc.record_success(name, health_group))
                logger.info("[%s] %s: %d건", label, name, len(items))
            except FutureTimeout:
                _record_failure(name, TimeoutError(f"{_SOURCE_TIMEOUT}s 타임아웃"))
            except ValueError as exc:
                _record_failure(name, exc, on_404=disable_on_404)
            except Exception as exc:
                _record_failure(name, exc)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    logger.info("[%s] 수집 완료: 총 %d건", label, len(all_items))
    return all_items
