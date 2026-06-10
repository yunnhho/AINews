"""그룹 B-2 — GitHub 주제별 트렌딩 리포지토리 수집 (일 1회, KST 00시)."""
import os
from datetime import UTC, datetime, timedelta

from celery.utils.log import get_task_logger

from pipeline.adapters.base import RawItem
from pipeline.adapters.github_trending import GitHubTrendingAdapter
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

_WINDOW_HOURS = 6.5

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

    since = datetime.now(UTC) - timedelta(hours=_WINDOW_HOURS)
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())
    token = os.getenv("GITHUB_TOKEN", "")
    all_items: list[RawItem] = []
    seen_urls: set[str] = set()

    for topic, min_stars in _B2_TOPICS:
        adapter = GitHubTrendingAdapter(topic=topic, min_stars=min_stars, token=token)
        if adapter.source_name in disabled:
            logger.info("[Group B-2] topic:%s 비활성화됨 — 스킵", topic)
            continue
        try:
            items = adapter.fetch(since)
            new_items = [i for i in items if i.url not in seen_urls]
            seen_urls.update(i.url for i in new_items)
            all_items.extend(new_items)
            health_svc.run_sync(health_svc.record_success(adapter.source_name, "GITHUB"))
            logger.info(
                "[Group B-2] topic:%s: %d건 (신규 %d건)", topic, len(items), len(new_items)
            )
        except Exception as exc:
            logger.warning("[Group B-2] topic:%s 실패: %s", topic, exc)
            health_svc.run_sync(
                health_svc.record_failure(adapter.source_name, "GITHUB", str(exc))
            )

    logger.info("[Group B-2] 수집 완료: 총 %d건", len(all_items))
    return all_items
