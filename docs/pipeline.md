# 배치 파이프라인 명세 — AI Pulse

> 기준 버전: PRD v3.0

## 스케줄

```
Cron: 0 0,6,12,18 * * * (KST)
실행 횟수: 하루 4회 (00:00 / 06:00 / 12:00 / 18:00)
수집 범위: 직전 6시간분 콘텐츠
```

## 단계별 처리 흐름

```
① 트리거
   └─ Celery Beat → 배치 태스크 큐 발행

② 소스별 병렬 수집 (직전 6시간분)
   ├─ [A] 뉴스 RSS        → feedparser
   ├─ [B] GitHub          → GitHub REST API
   ├─ [C] 엔지니어링 블로그 → feedparser (RSS)
   └─ [D] 뉴스레터        → Substack RSS / IMAP

③ 중복·유사 필터링
   ├─ URL 완전 일치 제거
   ├─ 제목 TF-IDF 유사도 ≥ 0.9 → 대표 1건만 유지
   └─ 이전 배치 처리 이력 제거

④ 카드 타입 자동 판정 (LLM)
   ├─ 코드 블록 / GitHub 링크 / "how to" → TECHNIQUE
   ├─ 모델 출시 / 기업 동향 / 시장 분석  → NEWS
   └─ 판정 불확실 → NEWS (안전 기본값)

⑤ Claude API 호출 (타입별 프롬프트)
   ├─ NEWS 프롬프트
   │   ├─ What / Why / Impact 구조 요약 (3~5문장)
   │   └─ 카테고리·태그·난이도 부여
   └─ TECHNIQUE 프롬프트
       ├─ 문제 / 핵심 아이디어 / 코드 / 주의점 구조
       ├─ 코드: 원본에서 추출만 (생성 금지, 최대 15줄)
       └─ 카테고리·태그·난이도·선행지식 부여

⑥ 번역 품질 검증 (영문 콘텐츠만)
   ├─ 역번역 (한→영) via Claude API
   ├─ 코사인 유사도 측정 via sentence-transformers (로컬)
   ├─ ≥ 0.85 → 통과
   ├─ < 0.85 → 재번역 (최대 3회)
   └─ 3회 실패 → 수동 검토 큐

⑦ 카드 생성 → DB 저장 → 캐시 갱신
   ├─ cards 테이블 INSERT
   ├─ card_tags 테이블 INSERT
   ├─ translation_logs 기록
   └─ Redis 피드 캐시 무효화

⑧ 배치 결과 로깅 (batch_logs 테이블)
   ├─ 소스 그룹별: 수집 N / 중복 제거 N / 발행 N
   ├─ 타입별: NEWS N장 / TECHNIQUE N장
   └─ API 비용: 토큰 N / 비용 $N
```

## 예상 처리량

| 구분 | 수량 |
|---|---|
| 배치당 수집 | 40~60건 |
| 중복 제거 후 | 20~30건 |
| 최종 발행 | 20~30장/배치 |
| TECHNIQUE 비중 | 30~40% |
| 일일 발행량 | 80~120장 (NEWS 50~70 + TECHNIQUE 30~50) |

## 에러 처리

| 상황 | 대응 |
|---|---|
| 배치 실패 | 15분 후 자동 재시도 (최대 2회) |
| 연속 2회 실패 | 관리자 Slack 알림 |
| GitHub API 403 | 다음 배치로 자동 연기 |
| 번역 3회 실패 | 수동 검토 큐로 이동 |
| 워커 OOM | `--max-tasks-per-child=50`, 컨테이너 2GB RAM |

## 번역 검증 파이프라인

```
원문(EN) ──→ 번역(KO)       ──→ 역번역(EN)         ──→ 유사도 비교
          [Claude API]      [Claude API]        [sentence-transformers]
                                                       │
                                                 ≥ 0.85 → 통과
                                                 < 0.85 → 재번역
                                                 3회 실패 → 수동 큐
```

**사용 모델**: `paraphrase-multilingual-MiniLM-L12-v2` (로컬, 500MB)

**비용 최적화**: 요약문(3~5문장)만 검증하여 토큰 최소화

## Celery 태스크 구조 (예정)

```
pipeline/
├── tasks/
│   ├── collect.py        # 소스 그룹별 수집 태스크
│   ├── deduplicate.py    # 중복 필터링
│   ├── classify.py       # 카드 타입 판정
│   ├── summarize.py      # Claude API 요약·번역
│   ├── verify.py         # 역번역 검증
│   └── publish.py        # DB 저장 + 캐시 갱신
├── adapters/
│   ├── rss.py            # 그룹 A
│   ├── github.py         # 그룹 B
│   ├── blog.py           # 그룹 C
│   └── newsletter.py     # 그룹 D
└── beat_schedule.py      # Celery Beat cron 정의
```
