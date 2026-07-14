"""그룹 B-3 — Awesome-* 리스트 README.md 커밋 diff로 신규 항목 감지."""
import os
from datetime import UTC, datetime

import httpx

from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.sources.common import collect_sources

_GITHUB_API = "https://api.github.com"

_B3_REPOS: list[dict] = [
    {"repo": "Hannibal046/Awesome-LLM", "name": "Awesome-LLM"},
    {"repo": "e2b-dev/awesome-ai-agents", "name": "awesome-ai-agents"},
    {"repo": "aishwaryanr/awesome-generative-ai-guide", "name": "awesome-generative-ai-guide"},
    {"repo": "punkpeye/awesome-mcp-servers", "name": "awesome-mcp-servers"},
]


def _fetch_readme_additions(repo: str, since: datetime, token: str) -> list[str]:
    """README.md 커밋 diff에서 since 이후 추가된 마크다운 리스트 항목만 반환."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{_GITHUB_API}/repos/{repo}/commits",
                headers=headers,
                params={"path": "README.md", "since": since.isoformat(), "per_page": 10},
            )
    except Exception:
        return []

    if resp.status_code != 200:
        return []

    commits = resp.json()
    if not commits:
        return []

    added_lines: list[str] = []
    diff_headers = {**headers, "Accept": "application/vnd.github.diff"}

    for commit in commits:
        sha = commit.get("sha", "")
        if not sha:
            continue
        try:
            with httpx.Client(timeout=30) as client:
                diff_resp = client.get(
                    f"{_GITHUB_API}/repos/{repo}/commits/{sha}",
                    headers=diff_headers,
                )
        except Exception:
            continue

        if diff_resp.status_code != 200:
            continue

        for line in diff_resp.text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                stripped = line[1:].strip()
                # 마크다운 리스트 항목 (링크 포함)만 추출
                if (stripped.startswith("- [") or stripped.startswith("* [")) and "http" in stripped:
                    added_lines.append(stripped)

    return added_lines


def _make_fetcher(repo: str, name: str, token: str):
    def fetch(since: datetime) -> list[RawItem]:
        added_lines = _fetch_readme_additions(repo, since, token)
        if not added_lines:
            return []
        return [
            RawItem(
                url=f"https://github.com/{repo}",
                title=f"{name} — {len(added_lines)}개 신규 항목",
                content="\n".join(added_lines),
                published_at=datetime.now(UTC),
                source_name=name,
                source_group=SourceGroup.GITHUB,
                original_lang="en",
                extra={"repo": repo, "new_entry_count": len(added_lines)},
            )
        ]

    return fetch


def collect_group_b3() -> list[RawItem]:
    """B-3 Awesome 리스트 README 신규 항목 수집."""
    token = os.getenv("GITHUB_TOKEN", "")
    fetchers = [
        (src["name"], _make_fetcher(src["repo"], src["name"], token)) for src in _B3_REPOS
    ]
    return collect_sources("Group B-3", "GITHUB", fetchers)
