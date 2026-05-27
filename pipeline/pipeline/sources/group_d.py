"""그룹 D-1 — Substack 뉴스레터 RSS 소스 4개 수집."""
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.adapters.rss import RSSAdapter
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

_WINDOW_HOURS = 6.5

_D1_SOURCES: list[dict] = [
    {
        "url": "https://www.latent.space/feed",
        "name": "Latent Space",
        "lang": "en",
    },
    {
        "url": "https://importai.substack.com/feed",
        "name": "Import AI",
        "lang": "en",
    },
    {
        "url": "https://www.deeplearning.ai/the-batch/feed/",
        "name": "The Batch (DeepLearning.AI)",
        "lang": "en",
    },
    {
        "url": "https://magazine.sebastianraschka.com/feed",
        "name": "Ahead of AI",
        "lang": "en",
    },
]


def collect_group_d1() -> list[RawItem]:
    """D-1 Substack 뉴스레터 수집. Celery 태스크에서 동기 호출."""
    since = datetime.now(timezone.utc) - timedelta(hours=_WINDOW_HOURS)
    all_items: list[RawItem] = []

    for src in _D1_SOURCES:
        adapter = RSSAdapter(
            feed_url=src["url"],
            source_name=src["name"],
            source_group=SourceGroup.NEWSLETTER,
            original_lang=src["lang"],
        )
        try:
            items = adapter.fetch(since)
            all_items.extend(items)
            health_svc.run_sync(health_svc.record_success(src["name"], "NEWSLETTER"))
            logger.info(f"[Group D-1] {src['name']}: {len(items)}건")
        except Exception as exc:
            logger.warning(f"[Group D-1] {src['name']} 실패: {exc}")
            health_svc.run_sync(health_svc.record_failure(src["name"], "NEWSLETTER", str(exc)))

    logger.info(f"[Group D-1] 수집 완료: 총 {len(all_items)}건")
    return all_items
