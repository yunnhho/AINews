"""그룹 B-1 — GitHub Releases API 소스 9개 수집."""
import os
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem
from pipeline.adapters.github import GitHubReleasesAdapter
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

_WINDOW_HOURS = 6.5

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
    since = datetime.now(timezone.utc) - timedelta(hours=_WINDOW_HOURS)
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())
    token = os.getenv("GITHUB_TOKEN", "")
    all_items: list[RawItem] = []

    for repo in _B1_REPOS:
        source_name = repo.split("/")[-1]
        if source_name in disabled:
            logger.info(f"[Group B-1] {repo}: 비활성화됨 — 스킵")
            continue
        adapter = GitHubReleasesAdapter(repo=repo, token=token)
        try:
            items = adapter.fetch(since)
            all_items.extend(items)
            health_svc.run_sync(health_svc.record_success(source_name, "GITHUB"))
            logger.info(f"[Group B-1] {repo}: {len(items)}건")
        except ValueError as exc:
            # 404 → 비활성화
            logger.warning(f"[Group B-1] {repo} 404: {exc}")
            health_svc.run_sync(health_svc.record_failure(source_name, "GITHUB", str(exc), disable_on_404=True))
        except Exception as exc:
            logger.warning(f"[Group B-1] {repo} 실패: {exc}")
            health_svc.run_sync(health_svc.record_failure(source_name, "GITHUB", str(exc)))

    logger.info(f"[Group B-1] 수집 완료: 총 {len(all_items)}건")
    return all_items
