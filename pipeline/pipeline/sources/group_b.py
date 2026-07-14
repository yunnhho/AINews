"""그룹 B-1 — GitHub Releases API 소스 9개 수집."""
import os

from pipeline.adapters.base import RawItem
from pipeline.adapters.github import GitHubReleasesAdapter
from pipeline.sources.common import collect_sources

_B1_REPOS: list[str] = [
    "langchain-ai/langchain",
    "run-llama/llama_index",
    "microsoft/autogen",
    "joaomdmoura/crewAI",
    "stanfordnlp/dspy",
    "modelcontextprotocol/servers",
    "vercel/ai",
    "pydantic/pydantic-ai",
    "huggingface/transformers",
]


def collect_group_b1() -> list[RawItem]:
    """B-1 GitHub Releases 수집. Celery 태스크에서 동기 호출."""
    token = os.getenv("GITHUB_TOKEN", "")
    fetchers = [
        (repo.split("/")[-1], GitHubReleasesAdapter(repo=repo, token=token).fetch)
        for repo in _B1_REPOS
    ]
    # GitHubReleasesAdapter는 404를 ValueError로 던진다 → 소스 자동 비활성화
    return collect_sources("Group B-1", "GITHUB", fetchers, disable_on_404=True)
