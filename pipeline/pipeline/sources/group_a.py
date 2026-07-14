"""그룹 A — 뉴스 RSS 소스 9개 수집."""
from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.adapters.hackernews import HackerNewsAdapter
from pipeline.adapters.rss import RSSAdapter
from pipeline.sources.common import collect_sources

# (url, name, lang)
_RSS_SOURCES: list[tuple[str, str, str]] = [
    ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch AI", "en"),
    ("https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "The Verge AI", "en"),
    ("https://www.technologyreview.com/topic/artificial-intelligence/feed/", "MIT Technology Review AI", "en"),
    ("https://export.arxiv.org/rss/cs.AI", "arXiv cs.AI", "en"),
    ("https://export.arxiv.org/rss/cs.CL", "arXiv cs.CL", "en"),
    ("https://www.aitimes.com/rss/allArticle.xml", "AI타임스", "ko"),
    ("https://news.hada.io/rss", "GeekNews", "ko"),
    ("https://yozm.wishket.com/magazine/rss/", "요즘IT", "ko"),
]

# 인공지능신문은 RSS 없음 — 웹 크롤링 미구현 (Phase 2에서 추가 예정)


def collect_group_a() -> list[RawItem]:
    """그룹 A 전체 소스 수집. Celery 태스크에서 동기 호출."""
    fetchers = [
        (
            name,
            RSSAdapter(
                feed_url=url,
                source_name=name,
                source_group=SourceGroup.NEWS_RSS,
                original_lang=lang,
            ).fetch,
        )
        for url, name, lang in _RSS_SOURCES
    ]
    fetchers.append(("Hacker News", HackerNewsAdapter().fetch))
    return collect_sources("Group A", "NEWS_RSS", fetchers)
