"""Claude 호출 공통 상수 + 응답 파서 (news/technique 처리기 공용)."""
import json

MODEL = "claude-haiku-4-5-20251001"
VALID_CATEGORIES = {"CODING", "DESIGN", "GENERAL"}
VALID_DIFFICULTIES = {"BEGINNER", "INTERMEDIATE", "ADVANCED"}


def parse_json_response(raw: str) -> dict | None:
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
