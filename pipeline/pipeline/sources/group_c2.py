"""그룹 C-2 — 개인 엔지니어 블로그 RSS 수집 (5개)."""
from datetime import UTC, datetime, timedelta

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.adapters.rss import RSSAdapter
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

_WINDOW_HOURS = 6.5

_C2_SOURCES: list[dict] = [
    {
        "url": "https://simonwillison.net/atom/everything/",
        "name": "Simon Willison",
        "lang": "en",
    },
    {
        "url": "https://eugeneyan.com/feed.xml",
        "name": "Eugene Yan",
        "lang": "en",
    },
    {
        "url": "https://lilianweng.github.io/index.xml",
        "name": "Lilian Weng",
        "lang": "en",
    },
    {
        "url": "https://huyenchip.com/feed.xml",
        "name": "Chip Huyen",
        "lang": "en",
    },
    {
        "url": "https://hamel.dev/feed.xml",
        "name": "Hamel Husain",
        "lang": "en",
    },
]


def collect_group_c2() -> list[RawItem]:
    """C-2 개인 엔지니어 블로그 수집."""
    since = datetime.now(UTC) - timedelta(hours=_WINDOW_HOURS)
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())
    all_items: list[RawItem] = []

    for src in _C2_SOURCES:
        if src["name"] in disabled:
            logger.info("[Group C-2] %s: 비활성화됨 — 스킵", src["name"])
            continue
        adapter = RSSAdapter(
            feed_url=src["url"],
            source_name=src["name"],
            source_group=SourceGroup.ENG_BLOG,
            original_lang=src["lang"],
        )
        try:
            items = adapter.fetch(since)
            all_items.extend(items)
            health_svc.run_sync(health_svc.record_success(src["name"], "ENG_BLOG"))
            logger.info("[Group C-2] %s: %d건", src["name"], len(items))
        except Exception as exc:
            logger.warning("[Group C-2] %s 실패: %s", src["name"], exc)
            health_svc.run_sync(
                health_svc.record_failure(src["name"], "ENG_BLOG", str(exc))
            )

    logger.info("[Group C-2] 수집 완료: 총 %d건", len(all_items))
    return all_items
