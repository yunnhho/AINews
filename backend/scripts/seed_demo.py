"""결정적(idempotent) 데모 시드 — 4개 머니샷을 항상 같은 상태로 재현한다.

  1) 배치 파이프라인: RSS 609 + GitHub 8 → 디듀프 후 562 (batch_logs 타임라인)
  2) 번역 환각 게이트: 통과 카드 2건(sim 0.887/0.912) + 검토큐 카드 3건(sim 0.70대)
  3) 비용 통제: 최근 14일 × KST 4배치(배치당 ≈$2)로 현실적 일별 토큰·비용 KPI + 월 $20 예산 게이지
  4) 한국어 검색: nori 형태소 검색용 한국어 카드(Elasticsearch 색인 포함)

실행:  python -m scripts.seed_demo         (backend/ 디렉터리에서)
    또는  docker compose exec api python -m scripts.seed_demo

여러 번 실행해도 동일한 상태가 된다(고정 ID를 먼저 삭제 후 재삽입).
Elasticsearch가 없으면 색인만 건너뛰고 나머지는 그대로 시드한다.
"""
import asyncio
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.batch import BatchLog, BatchStatus, SourceHealth, TranslationLog
from app.models.card import Card, CardTag, CardType, Category, Difficulty, OriginalLang, SourceGroup, Tag

# 고정 ID 범위 — 재실행 시 이 범위를 먼저 지우고 다시 넣는다(실데이터와 충돌 방지).
CARD_ID_BASE = 900_000
TAG_ID_BASE = 90_000
# 배치당 비용 ≈ 562 카드 × $0.0037 ≈ $2.08 (haiku 4.5 단가 기준, 실제 과금 아님)
COST_PER_CARD = 0.0037
KST = timezone(timedelta(hours=9))

# ── 태그 (slug 고정) ────────────────────────────────
TAGS = [
    (TAG_ID_BASE + 1, "claude", "claude"),
    (TAG_ID_BASE + 2, "llm", "llm"),
    (TAG_ID_BASE + 3, "ai-news", "ai-news"),
    (TAG_ID_BASE + 4, "prompt-caching", "prompt-caching"),
    (TAG_ID_BASE + 5, "nori", "nori"),
    (TAG_ID_BASE + 6, "korean-search", "korean-search"),
    (TAG_ID_BASE + 7, "elasticsearch", "elasticsearch"),
    (TAG_ID_BASE + 8, "rag", "rag"),
    (TAG_ID_BASE + 9, "agent", "agent"),
    (TAG_ID_BASE + 10, "tool-use", "tool-use"),
]


def _news(cid, title, summary, key_points, tags, *, published, lang=OriginalLang.KO, cat=Category.GENERAL):
    return dict(
        id=cid, card_type=CardType.NEWS, title=title, summary=summary, key_points=key_points,
        source_url=f"https://demo.aipulse.kr/news/{cid}", source_name="AI Pulse Demo",
        source_group=SourceGroup.NEWS_RSS, original_lang=lang, category=cat,
        difficulty=Difficulty.BEGINNER, is_published=published, tags=tags,
    )


def _tech(cid, title, summary, problem, idea, code, caveats, tags, *, published, cat=Category.CODING):
    return dict(
        id=cid, card_type=CardType.TECHNIQUE, title=title, summary=summary,
        problem=problem, idea=idea, code_snippet=code, caveats=caveats, prerequisites="Python, LLM API",
        source_url=f"https://demo.aipulse.kr/tech/{cid}", source_name="AI Pulse Demo Eng",
        source_group=SourceGroup.ENG_BLOG, original_lang=OriginalLang.KO, category=cat,
        difficulty=Difficulty.INTERMEDIATE, is_published=published, tags=tags,
    )


# 통과 카드 2건(공개) + 검색용 공개 카드 + 검토큐 카드 3건(비공개 초안)
CARDS = [
    # ── 머니샷2: 통과 카드 2건 ──
    _news(CARD_ID_BASE + 1, "Anthropic, Claude Opus 4.8 공개 — 더 빠른 출력",
          "Anthropic이 Claude Opus 4.8을 공개했습니다. 코딩·에이전트 작업 성능이 향상되고 출력 속도가 빨라졌습니다.",
          ["Claude Opus 4.8이 공개되었습니다.", "코딩·도구 호출 성능이 개선되었습니다.", "비용은 유지되어 실무 도입 부담이 낮습니다."],
          ["claude", "llm", "ai-news"], published=True),
    _tech(CARD_ID_BASE + 2, "프롬프트 캐싱으로 반복 호출 비용 절감하기",
          "정적 프리픽스를 캐싱해 반복 호출 비용을 크게 줄이는 기법입니다.",
          "동일한 시스템 프롬프트를 매 호출마다 다시 전송해 입력 토큰 비용이 낭비됩니다.",
          "cache_control로 정적 프리픽스를 캐싱해 재사용하면 입력 비용을 최대 90% 절감합니다.",
          "client.messages.create(system=[{'type':'text','text':PREFIX,'cache_control':{'type':'ephemeral'}}])",
          ["캐시 TTL(5분)을 넘기면 재계산됩니다.", "짧은 프리픽스는 캐싱 이득이 작습니다."],
          ["prompt-caching", "llm"], published=True),
    # ── 머니샷4: 한국어 검색용 공개 카드 ──
    _news(CARD_ID_BASE + 6, "한국어 검색 정확도 개선기 — nori 형태소 분석",
          "Elasticsearch nori 분석기로 한국어 검색 재현율을 끌어올린 사례입니다.",
          ["nori 형태소 분석기를 도입했습니다.", "'검색'과 '검색어'를 같은 어간으로 묶습니다.", "재현율이 크게 향상되었습니다."],
          ["nori", "korean-search", "elasticsearch"], published=True, cat=Category.CODING),
    _tech(CARD_ID_BASE + 7, "RAG 파이프라인에서 검색 재현율 높이는 법",
          "한국어 RAG에서 형태소 색인과 하이브리드 검색으로 재현율을 높입니다.",
          "임베딩 검색만으로는 한국어 정확 일치·희귀어 재현율이 낮습니다.",
          "형태소 기반 키워드 검색과 임베딩 검색을 결합한 하이브리드 검색으로 재현율을 보완합니다.",
          None,
          ["가중치 튜닝이 필요합니다.", "색인 비용이 증가합니다."],
          ["rag", "korean-search", "elasticsearch"], published=True),
    _news(CARD_ID_BASE + 8, "LLM 에이전트 도구 호출 신뢰성 높이기",
          "에이전트의 도구 호출 실패를 줄이는 검증 게이트 패턴을 소개합니다.",
          ["도구 호출 스키마를 엄격히 검증합니다.", "실패 시 재시도·폴백을 둡니다.", "관측성으로 회귀를 추적합니다."],
          ["agent", "tool-use", "llm"], published=True, cat=Category.CODING),
    # ── 머니샷2: 검토큐 카드 3건(sim 0.70대, 비공개 초안) ──
    _news(CARD_ID_BASE + 3, "[검토대기] GPT 계열 벤치마크 논쟁 요약",
          "벤치마크 해석을 둘러싼 논쟁을 정리했습니다. (역번역 유사도 미달로 검토 대기)",
          ["새 벤치마크가 공개되었습니다.", "측정 방식에 이견이 있습니다.", "재현성 검증이 필요합니다."],
          ["llm", "ai-news"], published=False, lang=OriginalLang.EN),
    _tech(CARD_ID_BASE + 4, "[검토대기] 분산 학습 체크포인트 최적화",
          "체크포인트 저장 오버헤드를 줄이는 기법. (역번역 유사도 미달로 검토 대기)",
          "대규모 학습에서 체크포인트 저장이 학습을 지연시킵니다.",
          "비동기 샤딩 저장으로 지연을 숨깁니다.",
          None,
          ["스토리지 대역폭에 민감합니다.", "복구 절차 검증이 필요합니다."],
          ["llm"], published=False),
    _news(CARD_ID_BASE + 5, "[검토대기] 오픈소스 임베딩 모델 비교",
          "임베딩 모델 성능 비교 요약. (역번역 유사도 미달로 검토 대기)",
          ["여러 임베딩 모델을 비교했습니다.", "언어별 편차가 큽니다.", "용도별 선택이 필요합니다."],
          ["llm", "rag"], published=False, lang=OriginalLang.EN),
]

# 카드별 역번역 로그 (머니샷2 게이트 시연)
#   통과: sim 0.887 / 0.912  |  검토큐: sim 0.712 / 0.688 / 0.734
TRANSLATION_LOGS = [
    (CARD_ID_BASE + 1, "Anthropic released Claude Opus 4.8 with faster output.",
     "Anthropic이 Claude Opus 4.8을 공개했습니다. 출력 속도가 빨라졌습니다.",
     "Anthropic unveiled Claude Opus 4.8 with faster output speed.", 0.887, True, 0),
    (CARD_ID_BASE + 2, "Prompt caching reuses a static prefix to cut input cost.",
     "정적 프리픽스를 캐싱해 반복 호출 비용을 절감합니다.",
     "Caching a static prefix reduces repeated call cost.", 0.912, True, 0),
    (CARD_ID_BASE + 3, "A dispute over how to interpret GPT-family benchmark results.",
     "GPT 계열 벤치마크 해석을 둘러싼 논쟁.",
     "An argument about interpreting benchmarks of the cat family.", 0.712, False, 2),
    (CARD_ID_BASE + 4, "Optimizing distributed training checkpoint overhead.",
     "분산 학습 체크포인트 저장 오버헤드 최적화.",
     "Improving the checkpoint of the distributed dyeing overhead.", 0.688, False, 2),
    (CARD_ID_BASE + 5, "Comparison of open-source embedding models across languages.",
     "오픈소스 임베딩 모델의 언어별 성능 비교.",
     "A comparison of open source embedding models by fish language.", 0.734, False, 2),
]

SOURCE_HEALTH = [
    ("Anthropic Blog (RSS)", "A", 0, True),
    ("Hacker News AI", "A", 0, True),
    ("GitHub Releases", "B1", 0, True),
    ("GitHub Trending (claude-md)", "B2", 2, True),   # 경보(2회 연속 실패)
    ("Engineering Blog Feeds", "C1", 0, True),
    ("Substack Newsletters", "D1", 4, False),         # critical(4회) + 비활성
]


def _es_doc(card: Card) -> dict:
    doc = {
        "id": card.id, "card_type": card.card_type.value, "category": card.category.value,
        "difficulty": card.difficulty.value, "title": card.title, "summary": card.summary,
        "source_url": card.source_url, "source_name": card.source_name,
        "like_count": card.like_count, "published_at": card.published_at.isoformat(),
        "tags": [t.name for t in card.tags],
    }
    if card.card_type == CardType.NEWS:
        doc["key_points"] = card.key_points or []
    else:
        doc.update(problem=card.problem, idea=card.idea, code_snippet=card.code_snippet,
                   caveats=card.caveats or [], prerequisites=card.prerequisites)
    return doc


def _build_batch_logs(now: datetime) -> list[BatchLog]:
    """현실적인 일별 분포 — 최근 14일 × KST 0/6/12/18시 배치(배치당 ≈$2).

    각 날짜에 하루 4배치가 고르게 쌓여 일별 비용 그래프가 자연스럽고(≈$8/일),
    월 예산 게이지는 '이번 달' 배치만 합산하므로 월초일수록 낮게(현실적) 나온다.
    가장 최근 배치는 헤드라인 지표(RSS 609 + GitHub 8 → 디듀프 562)를 담는다.
    """
    now_kst = now.astimezone(KST)
    timestamps: list[datetime] = []
    for d in range(14):           # d=0 → 오늘
        day = now_kst - timedelta(days=d)
        for hour in (0, 6, 12, 18):
            ts = day.replace(hour=hour, minute=0, second=0, microsecond=0).astimezone(UTC)
            if ts <= now:         # 아직 오지 않은 슬롯(오늘 이후)은 제외
                timestamps.append(ts)
    timestamps.sort()
    latest = timestamps[-1]

    logs: list[BatchLog] = []
    for k, ts in enumerate(timestamps):
        headline = ts == latest
        if headline:
            collected = {"A": 609, "B1": 8}
            dedup = 55
        else:
            collected = {"A": 540 + (k % 7) * 6, "B1": 4 + (k % 3)}
            dedup = 12 + (k % 9)
        total = sum(collected.values())
        published_total = total - dedup
        pub = {"NEWS": int(published_total * 0.7), "TECHNIQUE": published_total - int(published_total * 0.7)}
        logs.append(BatchLog(
            batch_id=f"demo-{ts:%Y%m%d-%H}h",
            scheduled_at=ts, started_at=ts, completed_at=ts + timedelta(minutes=7),
            status=BatchStatus.COMPLETED, collected_by_group=collected,
            deduplicated_count=dedup, published_by_type=pub, failed_count=0,
            api_tokens_used=int(published_total * 2050),
            api_cost_usd=Decimal(str(round(published_total * COST_PER_CARD, 4))),
        ))
    return logs


async def seed():
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        # ── ① 기존 데모 데이터 삭제(멱등) ──
        card_ids = [c["id"] for c in CARDS]
        # translation_logs / card_tags 는 카드 삭제 시 CASCADE 되지만 명시적으로도 지운다.
        await db.execute(delete(TranslationLog).where(TranslationLog.card_id.in_(card_ids)))
        await db.execute(delete(CardTag).where(CardTag.card_id.in_(card_ids)))
        await db.execute(delete(Card).where(Card.id.in_(card_ids)))
        # 태그는 실데이터와 slug를 공유할 수 있으므로 삭제하지 않고 재사용(아래에서 upsert).
        await db.execute(delete(BatchLog).where(BatchLog.batch_id.like("demo-%")))
        await db.execute(delete(SourceHealth).where(SourceHealth.source_name.in_([s[0] for s in SOURCE_HEALTH])))
        await db.flush()

        # ── ② 태그 (slug 기준 upsert — 실데이터 태그가 있으면 재사용) ──
        slugs = [t[2] for t in TAGS]
        tag_by_slug: dict[str, Tag] = {
            t.slug: t for t in (await db.execute(select(Tag).where(Tag.slug.in_(slugs)))).scalars().all()
        }
        for _tid, name, slug in TAGS:
            if slug not in tag_by_slug:
                tag = Tag(name=name, slug=slug, category=None)  # id는 DB가 부여
                db.add(tag)
                tag_by_slug[slug] = tag
        await db.flush()

        # ── ③ 카드 (+ 태그 연결) ──
        published_cards: list[Card] = []
        for idx, c in enumerate(CARDS):
            spec = dict(c)
            tags = [tag_by_slug[s] for s in spec.pop("tags")]
            card = Card(**spec, like_count=0, bookmark_count=0,
                        published_at=now - timedelta(hours=idx + 1),
                        batch_id="demo-seed")
            card.tags = tags
            db.add(card)
            if card.is_published:
                published_cards.append(card)
        await db.flush()

        # ── ④ 역번역 로그 (머니샷2) ──
        for card_id, orig, ko, back, sim, passed, retry in TRANSLATION_LOGS:
            db.add(TranslationLog(
                card_id=card_id, original_text=orig, translated_text=ko,
                back_translated_text=back, similarity_score=sim, passed=passed,
                retry_count=retry, created_at=now - timedelta(hours=1),
            ))

        # ── ⑤ 소스 헬스 ──
        for name, group, fails, enabled in SOURCE_HEALTH:
            db.add(SourceHealth(
                source_name=name, source_group=group,
                last_success_at=(now - timedelta(hours=fails * 6)) if fails < 4 else now - timedelta(days=2),
                consecutive_failures=fails, enabled=enabled,
                last_error_log=None if fails == 0 else "timeout while fetching feed",
            ))

        # ── ⑥ 배치 로그 (머니샷1·3) ──
        batch_logs = _build_batch_logs(now)
        for bl in batch_logs:
            db.add(bl)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_cost = sum(float(b.api_cost_usd) for b in batch_logs if b.scheduled_at >= month_start)

        await db.commit()

        # ── ⑦ Elasticsearch 색인 (머니샷4) — 없으면 건너뜀 ──
        try:
            from app.services import search as search_svc
            await search_svc.setup_index()
            for card in published_cards:
                await search_svc.index_card(_es_doc(card))
            es_msg = f"ES 색인 {len(published_cards)}건"
        except Exception as e:  # noqa: BLE001
            es_msg = f"ES 색인 건너뜀({type(e).__name__})"

    print("✅ 데모 시드 완료")
    print(f"   · 카드 {len(CARDS)}건 (공개 {len(published_cards)} / 검토큐 {len(CARDS) - len(published_cards)})")
    print(f"   · 역번역 로그 {len(TRANSLATION_LOGS)}건 (통과 2 / 검토 3)")
    print(f"   · 배치 로그 {len(batch_logs)}건 (최근 14일 × KST 4배치, 이달 누적 ≈ ${month_cost:.2f} / 예산 $20)")
    print(f"   · 소스 헬스 {len(SOURCE_HEALTH)}건 · {es_msg}")


if __name__ == "__main__":
    asyncio.run(seed())
