"""데모 모드 — 외부 소스 호출 없이 고정 스냅샷에서 RawItem을 생성한다.

공개 데모/영상에서 `run_batch`를 실행해도 실제 RSS/GitHub를 때리지 않고
결정적인 스냅샷으로 수집 → 디듀프 → (재생)AI 처리 → 발행 흐름을 보여준다.
디듀프 시연을 위해 일부 항목을 URL/제목 중복으로 넣어 둔다.
"""
from datetime import UTC, datetime, timedelta

from pipeline.adapters.base import RawItem, SourceGroup

_NOW = datetime(2026, 7, 1, 3, 0, tzinfo=UTC)


def collect_demo_snapshot() -> tuple[list[RawItem], dict[str, int]]:
    """(raw_items, collected_by_group) 반환. 항상 동일한 결과(결정적)."""
    items: list[RawItem] = [
        RawItem(
            url="https://demo.aipulse.kr/news/anthropic-claude-opus-4-8",
            title="Anthropic이 Claude Opus 4.8을 공개했습니다",
            content="Anthropic released Claude Opus 4.8 with faster output and improved coding. "
            "The model improves agentic tasks and tool use while keeping cost stable.",
            published_at=_NOW - timedelta(hours=1),
            source_name="Anthropic Blog",
            source_group=SourceGroup.NEWS_RSS,
            original_lang="en",
        ),
        # 디듀프용: 위와 사실상 동일 주제(제목 유사 → TF-IDF로 제거 시연)
        RawItem(
            url="https://demo.aipulse.kr/news/claude-opus-4-8-launch-mirror",
            title="Anthropic, Claude Opus 4.8 출시 — 더 빠른 출력",
            content="Anthropic announced Claude Opus 4.8, featuring faster output and better coding.",
            published_at=_NOW - timedelta(hours=1, minutes=5),
            source_name="Tech Mirror",
            source_group=SourceGroup.NEWS_RSS,
            original_lang="en",
        ),
        RawItem(
            url="https://demo.aipulse.kr/tech/prompt-caching-guide",
            title="프롬프트 캐싱으로 반복 호출 비용 90% 절감하기",
            content="Prompt caching lets you reuse a large static prefix across calls.\n\n"
            "```python\nclient.messages.create(system=[{'type':'text','text':PREFIX,"
            "'cache_control':{'type':'ephemeral'}}])\n```\n",
            published_at=_NOW - timedelta(hours=2),
            source_name="Engineering Blog",
            source_group=SourceGroup.ENG_BLOG,
            original_lang="en",
        ),
        RawItem(
            url="https://demo.aipulse.kr/tech/nori-korean-search",
            title="nori 형태소 분석기로 한국어 검색 재현율 높이기",
            content="한국어 검색은 형태소 단위 색인이 핵심입니다. Elasticsearch nori 분석기로 "
            "'검색'과 '검색어'를 같은 어간으로 묶어 재현율을 끌어올립니다.\n\n"
            "```json\n{\"analyzer\": \"nori\"}\n```\n",
            published_at=_NOW - timedelta(hours=3),
            source_name="AI Pulse Eng",
            source_group=SourceGroup.ENG_BLOG,
            original_lang="ko",
        ),
        # 디듀프용: 완전 동일 URL 중복(SHA-256 완전 일치로 제거 시연)
        RawItem(
            url="https://demo.aipulse.kr/news/anthropic-claude-opus-4-8",
            title="Anthropic이 Claude Opus 4.8을 공개했습니다 (재게시)",
            content="중복 URL — SHA-256 완전 일치로 제거되어야 합니다.",
            published_at=_NOW,
            source_name="Repost Bot",
            source_group=SourceGroup.NEWS_RSS,
            original_lang="en",
        ),
    ]
    # collected_by_group는 orchestrate와 동일한 키 구조를 사용한다.
    collected_by_group = {
        "A": 3, "B1": 0, "B2": 0, "B3": 0, "B4": 0,
        "C1": 2, "C2": 0, "D1": 0, "D2": 0,
    }
    return items, collected_by_group
