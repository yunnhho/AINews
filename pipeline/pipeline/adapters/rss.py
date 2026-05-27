"""feedparser 기반 RSS 어댑터."""
from datetime import datetime, timezone

import feedparser

from pipeline.adapters.base import BaseAdapter, RawItem, SourceGroup


class RSSAdapter(BaseAdapter):
    def __init__(
        self,
        feed_url: str,
        source_name: str,
        source_group: SourceGroup,
        original_lang: str = "en",
    ):
        self.feed_url = feed_url
        self.source_name = source_name
        self.source_group = source_group
        self.original_lang = original_lang

    def fetch(self, since: datetime) -> list[RawItem]:
        try:
            feed = feedparser.parse(self.feed_url)
        except Exception:
            return []

        items: list[RawItem] = []
        for entry in feed.entries:
            published = self._parse_date(entry)
            if published is None or published <= since:
                continue

            url = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            if not url or not title:
                continue

            content = self._extract_content(entry)
            items.append(
                RawItem(
                    url=url,
                    title=title,
                    content=content,
                    published_at=published,
                    source_name=self.source_name,
                    source_group=self.source_group,
                    original_lang=self.original_lang,
                )
            )
        return items

    # ── 내부 헬퍼 ──────────────────────────────────

    def _parse_date(self, entry) -> datetime | None:
        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            ts = getattr(entry, key, None) or entry.get(key)
            if ts:
                try:
                    return datetime(*ts[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
        return None

    def _extract_content(self, entry) -> str:
        if hasattr(entry, "content") and entry.content:
            return entry.content[0].get("value", "")
        return entry.get("summary", "")
