"""그룹 B-2 — GitHub 주제별 트렌딩 리포지토리 수집 (일 1회, KST 00시)."""
import os

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem
from pipeline.adapters.github_trending import GitHubTrendingAdapter
from pipeline.sources.common import collect_sources

logger = get_task_logger(__name__)

# (topic, min_stars) — content-sources.md B-2 기준
_B2_TOPICS: list[tuple[str, int]] = [
    ("llm", 100),
    ("llm-agents", 50),
    ("rag", 50),
    ("mcp", 30),
    ("ai-coding", 50),
    ("claude-md", 30),  # CLAUDE.md / 에이전트 설정 파일 관련 리포
]


def collect_group_b2(scheduled_hour: int = -1) -> list[RawItem]:
    """B-2 GitHub Trending 수집. KST 00시 배치(scheduled_hour=0)에서만 실행."""
    # 일 1회만 실행 — 수동 호출(-1)은 항상 허용
    if scheduled_hour not in (-1, 0):
        logger.info("[Group B-2] 00시 배치가 아님 — 스킵 (scheduled_hour=%d)", scheduled_hour)
        return []

    token = os.getenv("GITHUB_TOKEN", "")
    adapters = [
        GitHubTrendingAdapter(topic=topic, min_stars=min_stars, token=token)
        for topic, min_stars in _B2_TOPICS
    ]
    # topic 간 중복 URL은 파이프라인 공통 dedup 단계에서 제거된다.
    return collect_sources(
        "Group B-2", "GITHUB", [(a.source_name, a.fetch) for a in adapters]
    )
