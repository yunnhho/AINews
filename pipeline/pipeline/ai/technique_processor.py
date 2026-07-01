"""TECHNIQUE 카드 처리 — Claude API 4단 구조 생성."""
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pipeline.adapters.base import RawItem
from pipeline.ai.demo_client import get_client as _demo_get_client
from pipeline.ai.prompts import TECHNIQUE_SYSTEM, TECHNIQUE_USER

_MODEL = "claude-haiku-4-5-20251001"
_client = None
logger = logging.getLogger(__name__)

_VALID_CATEGORIES = {"CODING", "DESIGN", "GENERAL"}
_VALID_DIFFICULTIES = {"BEGINNER", "INTERMEDIATE", "ADVANCED"}
_CODE_BLOCK_RE = re.compile(r"```[\w]*\n(.*?)```", re.DOTALL)


def _get_client():
    # 데모 모드/키 미설정 시 재생 클라이언트로 대체(비용 이중 가드).
    global _client
    if _client is None:
        _client = _demo_get_client()
    return _client


@dataclass
class TechniqueCardData:
    title: str
    summary: str
    problem: str
    idea: str
    code_snippet: str | None
    caveats: list[str]
    prerequisites: str | None
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


def _extract_code_snippet(content: str) -> str | None:
    """원본 콘텐츠에서 가장 긴 코드 블록 추출 (LLM 생성 금지)."""
    matches = _CODE_BLOCK_RE.findall(content)
    if not matches:
        return None
    return max(matches, key=len).strip() or None


def _parse_response(raw: str) -> dict | None:
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


def process_technique(item: RawItem) -> TechniqueCardData | None:
    """TECHNIQUE 카드 데이터 생성. 실패 시 None 반환."""
    try:
        content_preview = item.content[:3000]
        msg = _get_client().messages.create(
            model=_MODEL,
            max_tokens=1500,
            system=TECHNIQUE_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": TECHNIQUE_USER.format(title=item.title, content=content_preview),
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
        problem = str(data.get("problem", "")).strip()
        idea = str(data.get("idea", "")).strip()
        caveats = [str(c) for c in data.get("caveats", [])]
        prerequisites_raw = data.get("prerequisites")
        prerequisites = str(prerequisites_raw).strip() if prerequisites_raw else None
        category = str(data.get("category", "CODING")).upper()
        tags = [str(t).lower().replace(" ", "-") for t in data.get("tags", [])]
        difficulty = str(data.get("difficulty", "INTERMEDIATE")).upper()

        if not problem or not idea:
            return None
        if not summary:
            summary = idea[:200]
        if category not in _VALID_CATEGORIES:
            category = "CODING"
        if difficulty not in _VALID_DIFFICULTIES:
            difficulty = "INTERMEDIATE"

        code_snippet = _extract_code_snippet(item.content)

        return TechniqueCardData(
            title=title,
            summary=summary,
            problem=problem,
            idea=idea,
            code_snippet=code_snippet,
            caveats=caveats[:3],
            prerequisites=prerequisites,
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
        logger.exception("TECHNIQUE 처리 실패: %s", item.url)
        return None
