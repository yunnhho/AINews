"""데모 모드 — Claude API 재생(replay) 클라이언트 + 비용 이중 가드.

공개 데모/영상 촬영에서 실제 크레딧을 태우지 않도록, `DEMO_MODE=true`이거나
`ANTHROPIC_API_KEY`가 비어 있으면 실제 anthropic.Anthropic 대신 기록된 응답을
돌려주는 `ReplayClient`를 반환한다.

이중 가드(둘 중 하나라도 안전하지 않으면 재생):
  1) DEMO_MODE=true            → 항상 재생
  2) ANTHROPIC_API_KEY 미설정   → 항상 재생 (환경변수 실수로 켜져도 과금 불가)
실제 호출은 DEMO_MODE=false AND 키가 있을 때만 발생한다(기본이 안전한 쪽).

news_processor / technique_processor / backtranslate 세 곳의 `_get_client()`가
이 모듈의 `get_client()`를 사용한다.
"""
import os
import re
from dataclasses import dataclass

# 재생 응답의 가상 토큰 수 — 카드 1건 ≈ $0.0037 (haiku 4.5: in $0.80/1M, out $4.00/1M)
# (1400 * 0.80 + 650 * 4.00) / 1e6 = $0.00372. 실제 과금은 발생하지 않는다(호출 자체가 없음).
_REPLAY_IN_TOKENS = 1400
_REPLAY_OUT_TOKENS = 650
_REPLAY_BT_IN_TOKENS = 210
_REPLAY_BT_OUT_TOKENS = 120

_TITLE_RE = re.compile(r"Title:\s*(.+)")


def is_demo_mode() -> bool:
    """데모 모드 여부 — 환경변수 하나로 켠다."""
    return os.getenv("DEMO_MODE", "false").strip().lower() in ("1", "true", "yes", "on")


def _use_replay() -> bool:
    """재생 사용 여부 (이중 가드). 실제 호출은 데모OFF + 키 존재일 때만."""
    if is_demo_mode():
        return True
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        return True
    return False


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class _Block:
    text: str
    type: str = "text"


@dataclass
class _Message:
    content: list
    usage: _Usage


def _extract_title(messages: list) -> str:
    """user 메시지에서 'Title: ...' 라인을 뽑아 카드가 입력마다 달라 보이게 한다."""
    for m in messages:
        content = m.get("content", "") if isinstance(m, dict) else ""
        match = _TITLE_RE.search(content)
        if match:
            return match.group(1).strip()[:80]
    return "AI 뉴스"


def _news_json(title: str) -> str:
    import json
    return json.dumps(
        {
            "title": f"{title}",
            "summary": f"{title} 관련 소식입니다. 핵심 변경점과 그 의미, 실무 영향을 카드로 정리했습니다.",
            "key_points": [
                f"{title}이(가) 공개되었습니다.",
                "기존 방식 대비 성능·비용 측면의 개선이 보고되었습니다.",
                "실무 적용 시 마이그레이션·호환성 검토가 필요합니다.",
            ],
            "category": "GENERAL",
            "tags": ["llm", "ai-news", "claude"],
            "difficulty": "BEGINNER",
        },
        ensure_ascii=False,
    )


def _technique_json(title: str) -> str:
    import json
    return json.dumps(
        {
            "title": f"{title}",
            "summary": f"{title} 기법의 문제·아이디어·주의점을 4단 구조로 정리했습니다.",
            "problem": "기존 접근은 반복 작업과 컨텍스트 유실로 정확도가 낮았습니다.",
            "idea": "핵심 단계를 구조화하고 캐싱·검증을 결합해 재현성과 품질을 높입니다.",
            "caveats": ["대규모 입력에서 지연이 증가할 수 있습니다.", "출력 검증 게이트를 반드시 함께 두세요."],
            "prerequisites": "Python, 기본 LLM API 사용 경험",
            "category": "CODING",
            "tags": ["technique", "llm", "prompt-engineering"],
            "difficulty": "INTERMEDIATE",
        },
        ensure_ascii=False,
    )


class _ReplayMessages:
    def create(self, *, model: str, max_tokens: int, system: str, messages: list, **kwargs):
        title = _extract_title(messages)
        sys = system or ""
        # system 프롬프트로 호출 종류를 구분한다.
        if "back-translation" in sys or "translator" in sys.lower():
            text = f"News about {title}. Key changes, why it matters, and practical impact."
            return _Message(
                content=[_Block(text=text)],
                usage=_Usage(_REPLAY_BT_IN_TOKENS, _REPLAY_BT_OUT_TOKENS),
            )
        if "technique" in sys.lower():
            text = _technique_json(title)
        else:
            text = _news_json(title)
        return _Message(
            content=[_Block(text=text)],
            usage=_Usage(_REPLAY_IN_TOKENS, _REPLAY_OUT_TOKENS),
        )


class ReplayClient:
    """anthropic.Anthropic 의 messages.create 인터페이스만 흉내내는 재생 클라이언트."""

    def __init__(self):
        self.messages = _ReplayMessages()


def get_client():
    """데모/키미설정이면 ReplayClient, 아니면 실제 anthropic.Anthropic 반환."""
    if _use_replay():
        return ReplayClient()
    import anthropic
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
