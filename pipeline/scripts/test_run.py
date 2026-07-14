"""테스트 배치 — 실제 소스에서 수집 후 최대 N건(기본 5)만 AI 처리·발행.

orchestrate._run_pipeline 의 로직을 그대로 따르되, AI 호출 건수를 N건으로 제한해
$20 크레딧 테스트에서 비용을 통제한다.

실행: docker compose run --rm worker python -m scripts.test_run [N]
"""
import sys
import uuid
from datetime import UTC, datetime

TEST_LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 5


# 테스트는 충분한 후보 확보를 위해 수집 윈도우를 넓힌다 (운영 배치는 6.5h).
WINDOW_HOURS = float(sys.argv[2]) if len(sys.argv) > 2 else 96.0


def main() -> None:
    from pipeline.sources import common
    common.WINDOW_HOURS = WINDOW_HOURS
    from pipeline.sources.group_a import collect_group_a
    from pipeline.sources.group_b import collect_group_b1
    from pipeline.sources.group_b4 import collect_group_b4

    batch_id = f"test-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    print(f"\n=== 테스트 배치 시작 [{batch_id}] limit={TEST_LIMIT} window={WINDOW_HOURS}h ===\n")

    # ① 수집 (큐레이션 CLAUDE.md + NEWS RSS + GitHub Releases)
    # B-4(큐레이션 파일)를 맨 앞에 둬 limit=1 실행 시 이 파일만 우선 처리되게 한다.
    raw_items = []
    try:
        b4 = collect_group_b4()
        print(f"[수집] Group B4 (큐레이션 CLAUDE.md): {len(b4)}건")
        raw_items += b4
    except Exception as e:
        print(f"[수집] Group B4 실패: {e}")
    try:
        a = collect_group_a()
        print(f"[수집] Group A (NEWS RSS): {len(a)}건")
        raw_items += a
    except Exception as e:
        print(f"[수집] Group A 실패: {e}")
    try:
        b1 = collect_group_b1()
        print(f"[수집] Group B1 (GitHub Releases): {len(b1)}건")
        raw_items += b1
    except Exception as e:
        print(f"[수집] Group B1 실패: {e}")

    print(f"[수집] 합계 {len(raw_items)}건")

    # ② 중복 제거
    from pipeline.filters.dedup import dedup
    filtered, dedup_cnt = dedup(raw_items)
    print(f"[디듀프] {dedup_cnt}건 제거 → {len(filtered)}건")

    # ③ N건만 잘라서 AI 처리
    subset = filtered[:TEST_LIMIT]
    print(f"[제한] AI 처리 대상 {len(subset)}건으로 제한\n")

    from pipeline.adapters.base import SourceGroup as SGroup
    from pipeline.ai.backtranslate import verify_translation
    from pipeline.ai.news_processor import process_news
    from pipeline.ai.publisher import publish_news_card, publish_technique_card
    from pipeline.ai.technique_processor import process_technique

    _NEWS_GROUPS = {SGroup.NEWS_RSS, SGroup.NEWSLETTER}
    _COST_IN = 0.80 / 1_000_000
    _COST_OUT = 4.00 / 1_000_000

    published = {"NEWS": 0, "TECHNIQUE": 0}
    drafts = 0
    failed = 0
    tokens = 0
    cost = 0.0

    for i, item in enumerate(subset, 1):
        is_news = item.source_group in _NEWS_GROUPS
        kind = "NEWS" if is_news else "TECHNIQUE"
        print(f"--- [{i}/{len(subset)}] {kind} | {item.title[:60]}")
        try:
            card = process_news(item) if is_news else process_technique(item)
            if card is None:
                print("    AI 처리 실패(None)")
                failed += 1
                continue
            tokens += card.input_tokens + card.output_tokens
            cost += card.input_tokens * _COST_IN + card.output_tokens * _COST_OUT

            if item.original_lang == "en":
                ref = item.title + ". " + item.content[:500]
                passed, score, back_text, bt_in, bt_out = verify_translation(ref, card.summary)
                tokens += bt_in + bt_out
                cost += bt_in * _COST_IN + bt_out * _COST_OUT
                print(f"    역번역 유사도 {score:.3f} → {'통과' if passed else '보류(검토큐)'}")
            else:
                passed, score, back_text = True, 1.0, None
                print("    한국어 원본 — 역번역 생략")

            if is_news:
                ok = publish_news_card(card, batch_id, back_text, score, passed)
            else:
                ok = publish_technique_card(card, batch_id, back_text, score, passed)

            if ok:
                published[kind] += 1
                print(f"    ✅ 발행: {card.title[:50]}")
            elif passed:
                failed += 1
                print("    ⚠️ 중복/저장실패")
            else:
                drafts += 1
                print("    📝 비공개 초안 저장(검토큐)")
        except Exception as e:
            failed += 1
            print(f"    예외: {e}")

    print("\n=== 결과 요약 ===")
    print(f"발행: NEWS={published['NEWS']}, TECHNIQUE={published['TECHNIQUE']}")
    print(f"검토큐 초안: {drafts} | 실패/중복: {failed}")
    print(f"토큰: {tokens:,} | 추정 비용: ${cost:.4f}")
    print("================\n")


if __name__ == "__main__":
    main()
