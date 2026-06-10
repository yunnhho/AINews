"""그룹 D-2 — IMAP 이메일 뉴스레터 수집 (4개)."""
from datetime import UTC, datetime, timedelta

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem
from pipeline.adapters.imap import IMAPAdapter
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

_WINDOW_HOURS = 6.5

_D2_SOURCES: list[dict] = [
    {"sender": "dan@tldrnewsletter.com", "name": "TLDR AI"},
    {"sender": "bens-bites@bensbites.beehiiv.com", "name": "Ben's Bites"},
    {"sender": "therundownai@mail.beehiiv.com", "name": "The Rundown AI"},
    {"sender": "contact@aiweekly.co", "name": "AI Engineer Weekly"},
]


def collect_group_d2() -> list[RawItem]:
    """D-2 IMAP 이메일 뉴스레터 수집."""
    since = datetime.now(UTC) - timedelta(hours=_WINDOW_HOURS)
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())
    all_items: list[RawItem] = []

    for src in _D2_SOURCES:
        if src["name"] in disabled:
            logger.info("[Group D-2] %s: 비활성화됨 — 스킵", src["name"])
            continue
        adapter = IMAPAdapter(sender_email=src["sender"], source_name=src["name"])
        try:
            items = adapter.fetch(since)
            all_items.extend(items)
            health_svc.run_sync(health_svc.record_success(src["name"], "NEWSLETTER"))
            logger.info("[Group D-2] %s: %d건", src["name"], len(items))
        except Exception as exc:
            logger.warning("[Group D-2] %s 실패: %s", src["name"], exc)
            health_svc.run_sync(
                health_svc.record_failure(src["name"], "NEWSLETTER", str(exc))
            )

    logger.info("[Group D-2] 수집 완료: 총 %d건", len(all_items))
    return all_items
