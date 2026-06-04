"""그룹 C-1 — 기업 엔지니어링 블로그 RSS 소스 8개 수집."""
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.adapters.rss import RSSAdapter
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

_WINDOW_HOURS = 6.5

_C1_SOURCES: list[dict] = [
    {
        "url": "https://www.anthropic.com/rss.xml",
        "name": "Anthropic Engineering",
        "lang": "en",
    },
    {
        "url": "https://openai.com/news/rss.xml",
        "name": "OpenAI Blog",
        "lang": "en",
    },
    {
        "url": "https://vercel.com/blog/rss.xml",
        "name": "Vercel AI Blog",
        "lang": "en",
    },
    {
        "url": "https://blog.langchain.dev/rss/",
        "name": "LangChain Blog",
        "lang": "en",
    },
    {
        "url": "https://www.llamaindex.ai/blog/rss.xml",
        "name": "LlamaIndex Blog",
        "lang": "en",
    },
    {
        "url": "https://huggingface.co/blog/feed.xml",
        "name": "Hugging Face Blog",
        "lang": "en",
    },
    {
        "url": "https://blog.replit.com/rss.xml",
        "name": "Replit Blog",
        "lang": "en",
    },
    {
        "url": "https://deepmind.google/research/blog.rss",
        "name": "Google DeepMind Blog",
        "lang": "en",
    },
]


def collect_group_c1() -> list[RawItem]:
    """C-1 엔지니어링 블로그 수집. Celery 태스크에서 동기 호출."""
    since = datetime.now(timezone.utc) - timedelta(hours=_WINDOW_HOURS)
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())
    all_items: list[RawItem] = []

    for src in _C1_SOURCES:
        if src["name"] in disabled:
            logger.info(f"[Group C-1] {src['name']}: 비활성화됨 — 스킵")
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
            logger.info(f"[Group C-1] {src['name']}: {len(items)}건")
        except Exception as exc:
            logger.warning(f"[Group C-1] {src['name']} 실패: {exc}")
            health_svc.run_sync(health_svc.record_failure(src["name"], "ENG_BLOG", str(exc)))

    logger.info(f"[Group C-1] 수집 완료: 총 {len(all_items)}건")
    return all_items
