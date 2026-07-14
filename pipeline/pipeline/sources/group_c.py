"""그룹 C-1 — 기업 엔지니어링 블로그 RSS 소스 8개 수집."""
from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.adapters.rss import RSSAdapter
from pipeline.sources.common import collect_sources

# (url, name)
_C1_SOURCES: list[tuple[str, str]] = [
    ("https://www.anthropic.com/rss.xml", "Anthropic Engineering"),
    ("https://openai.com/news/rss.xml", "OpenAI Blog"),
    ("https://vercel.com/blog/rss.xml", "Vercel AI Blog"),
    ("https://blog.langchain.dev/rss/", "LangChain Blog"),
    ("https://www.llamaindex.ai/blog/rss.xml", "LlamaIndex Blog"),
    ("https://huggingface.co/blog/feed.xml", "Hugging Face Blog"),
    ("https://blog.replit.com/rss.xml", "Replit Blog"),
    ("https://deepmind.google/research/blog.rss", "Google DeepMind Blog"),
]


def collect_group_c1() -> list[RawItem]:
    """C-1 엔지니어링 블로그 수집. Celery 태스크에서 동기 호출."""
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
        for url, name in _C1_SOURCES
    ]
    return collect_sources("Group C-1", "ENG_BLOG", fetchers)
