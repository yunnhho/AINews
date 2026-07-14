"""그룹 D-1 — Substack 뉴스레터 RSS 소스 4개 수집."""
from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.adapters.rss import RSSAdapter
from pipeline.sources.common import collect_sources

# (url, name)
_D1_SOURCES: list[tuple[str, str]] = [
    ("https://www.latent.space/feed", "Latent Space"),
    ("https://importai.substack.com/feed", "Import AI"),
    ("https://www.deeplearning.ai/the-batch/feed/", "The Batch (DeepLearning.AI)"),
    ("https://magazine.sebastianraschka.com/feed", "Ahead of AI"),
]


def collect_group_d1() -> list[RawItem]:
    """D-1 Substack 뉴스레터 수집. Celery 태스크에서 동기 호출."""
    fetchers = [
        (
            name,
            RSSAdapter(
                feed_url=url,
                source_name=name,
                source_group=SourceGroup.NEWSLETTER,
                original_lang="en",
            ).fetch,
        )
        for url, name in _D1_SOURCES
    ]
    return collect_sources("Group D-1", "NEWSLETTER", fetchers)
