"""그룹 A — 뉴스 RSS 소스 9개 수집."""
from datetime import UTC, datetime, timedelta

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.adapters.hackernews import HackerNewsAdapter
from pipeline.adapters.rss import RSSAdapter
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

# 수집 윈도우 (직전 배치 + 여유 30분)
_WINDOW_HOURS = 6.5

_RSS_SOURCES: list[dict] = [
    {
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "name": "TechCrunch AI",
        "lang": "en",
    },
    {
        "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "name": "The Verge AI",
        "lang": "en",
    },
    {
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "name": "MIT Technology Review AI",
        "lang": "en",
    },
    {
        "url": "https://export.arxiv.org/rss/cs.AI",
        "name": "arXiv cs.AI",
        "lang": "en",
    },
    {
        "url": "https://export.arxiv.org/rss/cs.CL",
        "name": "arXiv cs.CL",
        "lang": "en",
    },
    {
        "url": "https://www.aitimes.com/rss/allArticle.xml",
        "name": "AI타임스",
        "lang": "ko",
    },
    {
        "url": "https://news.hada.io/rss",
        "name": "GeekNews",
        "lang": "ko",
    },
    {
        "url": "https://yozm.wishket.com/magazine/rss/",
        "name": "요즘IT",
        "lang": "ko",
    },
]

# 인공지능신문은 RSS 없음 — 웹 크롤링 미구현 (Phase 2에서 추가 예정)


def collect_group_a() -> list[RawItem]:
    """그룹 A 전체 소스 수집. Celery 태스크에서 동기 호출."""
    since = datetime.now(UTC) - timedelta(hours=_WINDOW_HOURS)
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())
    all_items: list[RawItem] = []

    # RSS 소스
    for src in _RSS_SOURCES:
        if src["name"] in disabled:
            logger.info(f"[Group A] {src['name']}: 비활성화됨 — 스킵")
            continue
        adapter = RSSAdapter(
            feed_url=src["url"],
            source_name=src["name"],
            source_group=SourceGroup.NEWS_RSS,
            original_lang=src["lang"],
        )
        try:
            items = adapter.fetch(since)
            all_items.extend(items)
            health_svc.run_sync(health_svc.record_success(src["name"], "NEWS_RSS"))
            logger.info(f"[Group A] {src['name']}: {len(items)}건")
        except Exception as exc:
            logger.warning(f"[Group A] {src['name']} 실패: {exc}")
            health_svc.run_sync(health_svc.record_failure(src["name"], "NEWS_RSS", str(exc)))

    # Hacker News
    if "Hacker News" in disabled:
        logger.info("[Group A] Hacker News: 비활성화됨 — 스킵")
        return all_items
    hn_adapter = HackerNewsAdapter()
    try:
        hn_items = hn_adapter.fetch(since)
        all_items.extend(hn_items)
        health_svc.run_sync(health_svc.record_success("Hacker News", "NEWS_RSS"))
        logger.info(f"[Group A] Hacker News: {len(hn_items)}건")
    except Exception as exc:
        logger.warning(f"[Group A] Hacker News 실패: {exc}")
        health_svc.run_sync(health_svc.record_failure("Hacker News", "NEWS_RSS", str(exc)))

    logger.info(f"[Group A] 수집 완료: 총 {len(all_items)}건")
    return all_items
