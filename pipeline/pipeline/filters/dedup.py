"""URL SHA-256 해시 + TF-IDF 타이틀 유사도 중복 제거."""
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pipeline.adapters.base import RawItem

_TITLE_SIM_THRESHOLD = 0.9

# 재게시·공유 링크에 붙는 추적 파라미터 — URL 동일성 판단에서 제외한다.
_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_reader", "utm_name", "utm_social", "utm_brand",
    "fbclid", "gclid", "dclid", "gclsrc", "msclkid", "yclid",
    "mc_cid", "mc_eid", "igshid", "ref", "ref_src", "source", "spm",
})


def _normalize_url(url: str) -> str:
    """URL 정규화 — 스킴/호스트 소문자화, 추적 파라미터·프래그먼트 제거, 말미 슬래시 정리.

    같은 기사의 UTM 변형(`?utm_source=...`)이나 공유 프래그먼트(`#...`)를 동일 URL로 취급해
    배치 내 중복을 더 촘촘히 잡는다. 원본 URL 자체는 카드에 그대로 보존되고, 여기서 만든
    정규화 값은 오직 중복 판정 해시에만 쓴다. 파싱 실패 시 원본을 그대로 반환(안전).
    """
    try:
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower()
        netloc = parts.netloc.lower()
        query = urlencode(
            [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in _TRACKING_PARAMS]
        )
        path = parts.path.rstrip("/") or parts.path
        return urlunsplit((scheme, netloc, path, query, ""))  # fragment 제거
    except Exception:
        return url


def dedup(items: list[RawItem]) -> tuple[list[RawItem], int]:
    """배치 내 중복 제거. Returns (filtered_items, dedup_count)."""
    if not items:
        return [], 0

    dedup_count = 0
    seen_hashes: set[str] = set()
    unique: list[RawItem] = []

    # 1) URL SHA-256 기반 중복 제거 (추적 파라미터 정규화 후)
    for item in items:
        h = sha256(_normalize_url(item.url).encode()).hexdigest()
        if h in seen_hashes:
            dedup_count += 1
        else:
            seen_hashes.add(h)
            unique.append(item)

    if len(unique) <= 1:
        return unique, dedup_count

    # 2) TF-IDF 타이틀 유사도 중복 제거 (배치 내)
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        titles = [it.title for it in unique]
        vec = TfidfVectorizer(min_df=1, analyzer="char_wb", ngram_range=(2, 3))
        matrix = vec.fit_transform(titles)
        sim = cosine_similarity(matrix)

        keep = [True] * len(unique)
        for i in range(len(unique)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(unique)):
                if not keep[j]:
                    continue
                if sim[i, j] >= _TITLE_SIM_THRESHOLD:
                    # 더 긴 content 유지
                    if len(unique[i].content) >= len(unique[j].content):
                        keep[j] = False
                    else:
                        keep[i] = False
                        dedup_count += 1
                        break  # i가 폐기됐으므로 j 비교 불필요
                    dedup_count += 1

        unique = [it for it, k in zip(unique, keep) if k]
    except Exception:
        pass  # TF-IDF 실패 시 URL 중복 제거 결과 유지

    return unique, dedup_count
