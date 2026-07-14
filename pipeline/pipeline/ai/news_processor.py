"""NEWS 카드 처리 — Claude API 요약·분류 (한국어 출력)."""
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pipeline.adapters.base import RawItem
from pipeline.ai.common import MODEL, VALID_CATEGORIES, VALID_DIFFICULTIES, parse_json_response
from pipeline.ai.demo_client import get_client
from pipeline.ai.prompts import NEWS_SYSTEM, NEWS_USER

logger = logging.getLogger(__name__)


@dataclass
class NewsCardData:
    title: str
    summary: str
    key_points: list[str]
    category: str
    tags: list[str]
    difficulty: str
    original_lang: str
    # RawItem에서 전달되는 소스 메타데이터
    source_url: str = ""
    source_name: str = ""
    source_group: str = ""
    published_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    input_tokens: int = 0
    output_tokens: int = 0


def process_news(item: RawItem) -> NewsCardData | None:
    """NEWS 카드 데이터 생성. 실패 시 None 반환."""
    try:
        content_preview = item.content[:3000]
        msg = get_client().messages.create(
            model=MODEL,
            max_tokens=1024,
            system=NEWS_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": NEWS_USER.format(title=item.title, content=content_preview),
                }
            ],
        )
        in_tokens = msg.usage.input_tokens
        out_tokens = msg.usage.output_tokens

        data = parse_json_response(msg.content[0].text)
        if data is None:
            return None

        title = str(data.get("title", item.title))[:100]
        summary = str(data.get("summary", "")).strip()
        key_points = [str(p) for p in data.get("key_points", [])]
        category = str(data.get("category", "GENERAL")).upper()
        tags = [str(t).lower().replace(" ", "-") for t in data.get("tags", [])]
        difficulty = str(data.get("difficulty", "BEGINNER")).upper()

        if not summary or len(key_points) < 1:
            return None
        if category not in VALID_CATEGORIES:
            category = "GENERAL"
        if difficulty not in VALID_DIFFICULTIES:
            difficulty = "BEGINNER"

        return NewsCardData(
            title=title,
            summary=summary,
            key_points=key_points[:5],
            category=category,
            tags=tags[:5],
            difficulty=difficulty,
            original_lang=item.original_lang.upper(),
            source_url=item.url,
            source_name=item.source_name,
            source_group=item.source_group.value,
            published_at=item.published_at,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
        )

    except Exception:
        logger.exception("NEWS 처리 실패: %s", item.url)
        return None
