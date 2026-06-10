"""그룹 B-4 — 큐레이션 CLAUDE.md / 에이전트 설정 파일 직접 수집.

B-2(topic 검색)는 self-tagging된 리포만 잡으므로, topic이 없거나 오래된
핵심 CLAUDE.md(예: 17만 스타 andrej-karpathy-skills)는 놓친다. B-4는 큐레이션한
특정 파일 경로를 raw로 직접 가져온다. topic·푸시 시점과 무관하게 확실히 수집된다.

재과금 방지: 최근 윈도우를 쓰지 않으므로(오래된 파일도 첫 수집 대상),
수집 단계에서 source_url이 이미 DB에 있으면(발행분·초안 모두) 건너뛴다.
→ 이미 카드화된 파일은 네트워크·AI 비용이 발생하지 않는다.
"""
import os
from datetime import UTC, datetime

import httpx
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pipeline.adapters.base import RawItem, SourceGroup
from pipeline.models import source_health as health_svc

logger = get_task_logger(__name__)

_GITHUB_API = "https://api.github.com"
_MIN_CONTENT_LEN = 200  # 너무 짧은 스텁 파일 제외

# 큐레이션 파일 목록 — branch 미지정 시 "main".
# 사용자가 좋은 예시 URL을 줄 때마다 여기에 추가한다.
_B4_FILES: list[dict] = [
    {
        "repo": "multica-ai/andrej-karpathy-skills",
        "path": "CLAUDE.md",
        "branch": "main",
        "name": "andrej-karpathy-skills",
    },
]

_database_url = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://aipulse:aipulse@postgres:5432/aipulse"
)
# source_health와 동일 이유로 NullPool (run_sync가 매번 새 이벤트 루프 생성).
_engine = create_async_engine(_database_url, poolclass=NullPool)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _source_url_exists(url: str) -> bool:
    from app.models.card import Card

    async with _SessionLocal() as session:
        result = await session.execute(select(Card.id).where(Card.source_url == url))
        return result.scalar_one_or_none() is not None


def _blob_url(repo: str, branch: str, path: str) -> str:
    return f"https://github.com/{repo}/blob/{branch}/{path}"


def _fetch_file_text(repo: str, path: str, branch: str, token: str) -> str:
    """contents API로 파일 원문(raw)을 가져온다. 실패 시 빈 문자열."""
    headers = {
        "Accept": "application/vnd.github.raw",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{_GITHUB_API}/repos/{repo}/contents/{path}",
                headers=headers,
                params={"ref": branch},
            )
    except Exception:
        return ""
    if resp.status_code != 200:
        return ""
    return resp.text


def _fetch_last_commit_at(repo: str, path: str, branch: str, token: str) -> datetime:
    """해당 파일 경로의 최신 커밋 시각. 실패 시 현재 시각."""
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
                params={"path": path, "sha": branch, "per_page": 1},
            )
        commits = resp.json()
        date_str = commits[0]["commit"]["committer"]["date"]
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(UTC)


def collect_group_b4() -> list[RawItem]:
    """B-4 큐레이션 CLAUDE.md 수집. 이미 카드화된 파일은 수집 단계에서 스킵."""
    disabled = health_svc.run_sync(health_svc.get_disabled_sources())
    token = os.getenv("GITHUB_TOKEN", "")
    all_items: list[RawItem] = []

    for src in _B4_FILES:
        repo = src["repo"]
        path = src["path"]
        branch = src.get("branch", "main")
        name = src.get("name", repo.split("/")[-1])

        if name in disabled:
            logger.info("[Group B-4] %s: 비활성화됨 — 스킵", name)
            continue

        url = _blob_url(repo, branch, path)

        # 이미 수집된 파일이면 재처리(AI 비용)하지 않는다.
        if health_svc.run_sync(_source_url_exists(url)):
            logger.info("[Group B-4] %s: 이미 DB에 존재 — 스킵", name)
            health_svc.run_sync(health_svc.record_success(name, "GITHUB"))
            continue

        try:
            content = _fetch_file_text(repo, path, branch, token)
            if len(content.strip()) < _MIN_CONTENT_LEN:
                logger.info("[Group B-4] %s: 내용 짧음/없음 — 스킵", name)
                health_svc.run_sync(health_svc.record_success(name, "GITHUB"))
                continue

            published_at = _fetch_last_commit_at(repo, path, branch, token)
            all_items.append(
                RawItem(
                    url=url,
                    title=f"{repo} — {path}",
                    content=content,
                    published_at=published_at,
                    source_name=name,
                    source_group=SourceGroup.GITHUB,
                    original_lang="en",
                    extra={"repo": repo, "path": path, "branch": branch, "curated": True},
                )
            )
            health_svc.run_sync(health_svc.record_success(name, "GITHUB"))
            logger.info("[Group B-4] %s: 수집 (%d자)", name, len(content))
        except Exception as exc:
            logger.warning("[Group B-4] %s 실패: %s", name, exc)
            health_svc.run_sync(health_svc.record_failure(name, "GITHUB", str(exc)))

    logger.info("[Group B-4] 수집 완료: 총 %d건", len(all_items))
    return all_items
