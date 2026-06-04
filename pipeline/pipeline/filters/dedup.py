"""URL SHA-256 해시 + TF-IDF 타이틀 유사도 중복 제거."""
from hashlib import sha256

from pipeline.adapters.base import RawItem

_TITLE_SIM_THRESHOLD = 0.9


def dedup(items: list[RawItem]) -> tuple[list[RawItem], int]:
    """배치 내 중복 제거. Returns (filtered_items, dedup_count)."""
    if not items:
        return [], 0

    dedup_count = 0
    seen_hashes: set[str] = set()
    unique: list[RawItem] = []

    # 1) URL SHA-256 기반 중복 제거
    for item in items:
        h = sha256(item.url.encode()).hexdigest()
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
