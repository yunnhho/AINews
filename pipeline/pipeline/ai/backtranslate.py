"""역번역 검증 — Claude API(KO→EN) + sentence-transformers 코사인 유사도."""
import logging
import os

import anthropic

from pipeline.ai.prompts import BACKTRANSLATE_USER, TRANSLATE_SYSTEM

_MODEL = "claude-haiku-4-5-20251001"
_SIM_THRESHOLD = 0.85
_MAX_RETRIES = 3

_client: anthropic.Anthropic | None = None
_st_model = None
logger = logging.getLogger(__name__)


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    return _client


def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        _st_model = SentenceTransformer(name)
    return _st_model


def _cosine_sim(a: str, b: str) -> float:
    from sklearn.metrics.pairwise import cosine_similarity

    model = _get_st_model()
    vecs = model.encode([a[:500], b[:500]])
    return float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])


def verify_translation(
    original_en: str,
    ko_summary: str,
) -> tuple[bool, float, str | None, int, int]:
    """
    KO 요약을 EN으로 역번역 후 원문과 유사도 비교.
    Returns: (passed, similarity_score, back_translated_text, in_tokens, out_tokens)
    """
    total_in = 0
    total_out = 0
    last_back: str | None = None
    last_score = 0.0

    for _ in range(_MAX_RETRIES):
        try:
            msg = _get_client().messages.create(
                model=_MODEL,
                max_tokens=512,
                system=TRANSLATE_SYSTEM,
                messages=[{"role": "user", "content": BACKTRANSLATE_USER.format(text=ko_summary)}],
            )
            total_in += msg.usage.input_tokens
            total_out += msg.usage.output_tokens
            back_text = msg.content[0].text.strip()
            last_back = back_text

            score = _cosine_sim(original_en, back_text)
            last_score = score

            if score >= _SIM_THRESHOLD:
                return True, score, back_text, total_in, total_out

        except Exception:
            logger.warning("역번역 시도 실패 (재시도 중)", exc_info=True)

    return False, last_score, last_back, total_in, total_out
