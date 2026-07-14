"""소스 그룹 공통 수집 루프 — disabled 체크 → fetch → health 기록."""
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

WINDOW_HOURS = 6.5  # 수집 윈도우 (직전 배치 + 여유 30분)


def collect_sources(
    label: str,
    health_group: str,
    fetchers: list[tuple[str, Callable[[datetime], list[RawItem]]]],
    disable_on_404: bool = False,
) -> list[RawItem]:
    """(source_name, fetch(since)) 목록을 순회 수집. 실패는 소스 단위로 격리하고 health에 기록.

    disable_on_404=True면 fetch가 던진 ValueError(GitHub 어댑터의 404)로 소스를 자동 비활성화한다.
    """
    since = datetime.now(UTC) - timedelta(hours=WINDOW_HOURS)
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())
    all_items: list[RawItem] = []

    for name, fetch in fetchers:
        if name in disabled:
            logger.info("[%s] %s: 비활성화됨 — 스킵", label, name)
            continue
        try:
            items = fetch(since)
            all_items.extend(items)
            health_svc.run_sync(health_svc.record_success(name, health_group))
            logger.info("[%s] %s: %d건", label, name, len(items))
        except ValueError as exc:
            if not disable_on_404:
                logger.warning("[%s] %s 실패: %s", label, name, exc)
                health_svc.run_sync(health_svc.record_failure(name, health_group, str(exc)))
                continue
            logger.warning("[%s] %s 404: %s", label, name, exc)
            health_svc.run_sync(
                health_svc.record_failure(name, health_group, str(exc), disable_on_404=True)
            )
        except Exception as exc:
            logger.warning("[%s] %s 실패: %s", label, name, exc)
            health_svc.run_sync(health_svc.record_failure(name, health_group, str(exc)))

    logger.info("[%s] 수집 완료: 총 %d건", label, len(all_items))
    return all_items
