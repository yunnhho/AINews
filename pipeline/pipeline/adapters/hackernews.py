"""Hacker News Algolia Search API 어댑터."""
from datetime import UTC, datetime

import httpx

from pipeline.adapters.base import BaseAdapter, RawItem, SourceGroup

_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search_by_date"
_AI_QUERIES = ["LLM", "GPT", "Claude AI", "machine learning", "artificial intelligence", "RAG"]
_MIN_SCORE = 10
_HITS_PER_PAGE = 50


class HackerNewsAdapter(BaseAdapter):
    source_name = "Hacker News"
    source_group = SourceGroup.NEWS_RSS

    def fetch(self, since: datetime) -> list[RawItem]:
        since_ts = int(since.timestamp())
        seen_urls: set[str] = set()
        items: list[RawItem] = []

        for query in _AI_QUERIES:
            try:
                resp = httpx.get(
                    _ALGOLIA_URL,
                    params={
                        "tags": "story",
                        "query": query,
                        "numericFilters": f"created_at_i>{since_ts},points>={_MIN_SCORE}",
                        "hitsPerPage": _HITS_PER_PAGE,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                hits = resp.json().get("hits", [])
            except Exception:
                continue

            for hit in hits:
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                created_ts = hit.get("created_at_i")
                if not created_ts:
                    continue
                published_at = datetime.fromtimestamp(created_ts, tz=UTC)

                title = (hit.get("title") or "").strip()
                if not title:
                    continue

                content = hit.get("story_text") or ""
                items.append(
                    RawItem(
                        url=url,
                        title=title,
                        content=content,
                        published_at=published_at,
                        source_name=self.source_name,
                        source_group=self.source_group,
                        original_lang="en",
                        extra={"hn_points": hit.get("points", 0)},
                    )
                )

        return items
