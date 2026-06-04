"""GitHub Releases API 어댑터."""
import os
from datetime import datetime

import httpx

from pipeline.adapters.base import BaseAdapter, RawItem, SourceGroup
from pipeline.models import source_health as health_svc

_BASE_URL = "https://api.github.com"
_MIN_BODY_LEN = 300  # 300자 미만 릴리스 제외


class GitHubReleasesAdapter(BaseAdapter):
    source_group = SourceGroup.GITHUB

    def __init__(self, repo: str, token: str = ""):
        self.repo = repo
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.source_name = repo.split("/")[-1]

    def fetch(self, since: datetime) -> list[RawItem]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    f"{_BASE_URL}/repos/{self.repo}/releases",
                    headers=headers,
                    params={"per_page": 20},
                )
        except Exception:
            return []

        remaining = resp.headers.get("X-RateLimit-Remaining", "?")
        reset_ts = resp.headers.get("X-RateLimit-Reset", "?")

        if resp.status_code == 403:
            health_svc.run_sync(
                health_svc.record_failure(self.source_name, "GITHUB", "403 rate limit")
            )
            return []

        if resp.status_code == 404:
            # 리포 없음 → 호출 측에서 source_health 비활성화
            raise ValueError(f"404: {self.repo}")

        try:
            resp.raise_for_status()
            releases = resp.json()
        except Exception:
            return []

        items: list[RawItem] = []
        for release in releases:
            published_str = release.get("published_at") or release.get("created_at", "")
            if not published_str:
                continue
            try:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            if published_at <= since:
                continue

            body = release.get("body") or ""
            if len(body) < _MIN_BODY_LEN:
                continue  # 단순 버전업 제외

            tag = release.get("tag_name", "")
            url = release.get("html_url", f"https://github.com/{self.repo}/releases")
            title = f"{self.source_name} {tag}".strip()

            items.append(
                RawItem(
                    url=url,
                    title=title,
                    content=body,
                    published_at=published_at,
                    source_name=self.source_name,
                    source_group=self.source_group,
                    original_lang="en",
                    extra={
                        "repo": self.repo,
                        "tag": tag,
                        "rate_limit_remaining": remaining,
                        "rate_limit_reset": reset_ts,
                    },
                )
            )

        return items
