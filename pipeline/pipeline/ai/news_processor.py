"""NEWS 카드 처리 — Claude API 요약·분류 (한국어 출력)."""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

import anthropic

from pipeline.adapters.base import RawItem
from pipeline.ai.prompts import NEWS_SYSTEM, NEWS_USER

_MODEL = "claude-haiku-4-5-20251001"
_client: anthropic.Anthropic | None = None
logger = logging.getLogger(__name__)

_VALID_CATEGORIES = {"CODING", "DESIGN", "GENERAL"}
_VALID_DIFFICULTIES = {"BEGINNER", "INTERMEDIATE", "ADVANCED"}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    return _client


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
    published_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    input_tokens: int = 0
    output_tokens: int = 0


def _parse_response(raw: str) -> dict | None:
    """JSON 파싱 — 불완전한 응답에서도 JSON 블록 추출 시도."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
    return None


def process_news(item: RawItem) -> NewsCardData | None:
    """NEWS 카드 데이터 생성. 실패 시 None 반환."""
    try:
        content_preview = item.content[:3000]
        msg = _get_client().messages.create(
            model=_MODEL,
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

        data = _parse_response(msg.content[0].text)
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
        if category not in _VALID_CATEGORIES:
            category = "GENERAL"
        if difficulty not in _VALID_DIFFICULTIES:
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
