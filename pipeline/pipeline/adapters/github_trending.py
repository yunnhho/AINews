"""GitHub Search API 기반 AI/ML 주제 리포지토리 어댑터."""
import os
from datetime import datetime

import httpx

from pipeline.adapters.base import BaseAdapter, RawItem, SourceGroup

_SEARCH_URL = "https://api.github.com/search/repositories"


class GitHubTrendingAdapter(BaseAdapter):
    """GitHub Search API로 topic + 최소 별 수 기반 트렌딩 리포 수집."""

    source_group = SourceGroup.GITHUB

    def __init__(self, topic: str, min_stars: int = 50, token: str = ""):
        self.topic = topic
        self.min_stars = min_stars
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.source_name = f"github-trending-{topic}"

    def fetch(self, since: datetime) -> list[RawItem]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        since_str = since.strftime("%Y-%m-%d")
        query = f"topic:{self.topic} stars:>={self.min_stars} pushed:>{since_str}"

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    _SEARCH_URL,
                    headers=headers,
                    params={"q": query, "sort": "updated", "order": "desc", "per_page": 30},
                )
        except Exception:
            return []

        if resp.status_code in (403, 422):
            return []

        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        items: list[RawItem] = []
        for repo in data.get("items", []):
            pushed_at_str = repo.get("pushed_at") or repo.get("updated_at", "")
            if not pushed_at_str:
                continue
            try:
                pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            if pushed_at <= since:
                continue

            name = repo.get("full_name", "")
            description = repo.get("description") or ""
            html_url = repo.get("html_url", f"https://github.com/{name}")
            stars = repo.get("stargazers_count", 0)
            title = f"{name} (⭐{stars:,})"

            content_parts = [description]
            repo_topics = repo.get("topics", [])
            if repo_topics:
                content_parts.append(f"Topics: {', '.join(repo_topics)}")
            content = "\n".join(p for p in content_parts if p)

            if not content.strip():
                continue

            items.append(
                RawItem(
                    url=html_url,
                    title=title,
                    content=content,
                    published_at=pushed_at,
                    source_name=self.source_name,
                    source_group=self.source_group,
                    original_lang="en",
                    extra={
                        "repo": name,
                        "stars": stars,
                        "topic": self.topic,
                        "rate_limit_remaining": resp.headers.get("X-RateLimit-Remaining", "?"),
                    },
                )
            )

        return items
