"""그룹 C-2 — 개인 엔지니어 블로그 RSS 수집 (5개)."""
from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.adapters.rss import RSSAdapter
from pipeline.sources.common import collect_sources

# (url, name)
_C2_SOURCES: list[tuple[str, str]] = [
    ("https://simonwillison.net/atom/everything/", "Simon Willison"),
    ("https://eugeneyan.com/feed.xml", "Eugene Yan"),
    ("https://lilianweng.github.io/index.xml", "Lilian Weng"),
    ("https://huyenchip.com/feed.xml", "Chip Huyen"),
    ("https://hamel.dev/feed.xml", "Hamel Husain"),
]


def collect_group_c2() -> list[RawItem]:
    """C-2 개인 엔지니어 블로그 수집."""
    fetchers = [
        (
            name,
            RSSAdapter(
                feed_url=url,
                source_name=name,
                source_group=SourceGroup.ENG_BLOG,
                original_lang="en",
            ).fetch,
        )
        for url, name in _C2_SOURCES
    ]
    return collect_sources("Group C-2", "ENG_BLOG", fetchers)
