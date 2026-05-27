# 작업 단위 (컨텍스트 단위 Phase) — AI Pulse

> 각 Phase는 Claude Code 컨텍스트 1회 안에 완결되는 단위.
> 의존성 순서대로 진행. 병렬 가능한 항목은 `//` 표시.

---

## 전체 요약

| 그룹 | Phase | 이름 | 의존성 |
|---|---|---|---|
| 초기화 | P0-1 | 레포 구조 + Docker Compose + 환경변수 | — |
| 초기화 | P0-2 | DB 스키마 + Alembic 마이그레이션 | P0-1 |
| 백엔드 | P1-1 | FastAPI 앱 골격 (설정·미들웨어·헬스체크) | P0-2 |
| 백엔드 | P1-2 | 인증 모듈 (OAuth Google·GitHub + JWT) | P1-1 |
| 백엔드 | P1-3 | 카드 피드 API (조회·필터·페이지네이션·캐싱) | P1-1 |
| 백엔드 | P1-4 | 좋아요·북마크 API + 규칙 기반 추천 | P1-3 |
| 백엔드 | P1-5 | 검색 API + Meilisearch 인덱스 동기화 | P1-3 |
| 파이프라인 | P2-1 | Celery·Beat 기반 + 배치 오케스트레이터 + 로깅 | P0-2 |
| 파이프라인 | P2-2 | 소스 어댑터 — 그룹 A (뉴스 RSS) | P2-1 |
| 파이프라인 | P2-3 | 소스 어댑터 — 그룹 B-1 (GitHub Releases) | P2-1 |
| 파이프라인 | P2-4 | 소스 어댑터 — 그룹 C-1 + D-1 (블로그·Substack) | P2-1 |
| 파이프라인 | P2-5 | 중복 필터링 (URL 완전 일치 + TF-IDF) | P2-2,3,4 |
| 파이프라인 | P2-6 | Claude API — NEWS 요약·번역·분류 | P2-5 |
| 파이프라인 | P2-7 | Claude API — TECHNIQUE 요약·번역 + 역번역 검증 | P2-6 |
| 웹 프론트 | P3-1 | Next.js 15 프로젝트 + 레이아웃 + API 클라이언트 | P1-3 |
| 웹 프론트 | P3-2 | 카드 피드 페이지 (무한 스크롤·탭·타입 필터) | P3-1 |
| 웹 프론트 | P3-3 | NEWS 카드 컴포넌트 + 상세 펼치기 | P3-2 |
| 웹 프론트 | P3-4 | TECHNIQUE 카드 컴포넌트 (Shiki 코드 블록) | P3-2 |
| 웹 프론트 | P3-5 | 인증 UI + 소셜 로그인 + 좋아요·북마크 인터랙션 | P3-3,4 // P1-2 |
| 웹 프론트 | P3-6 | SEO + OG 이미지 생성 + 공유 기능 + PWA | P3-5 |
| 관리자 | P4-1 | 관리 대시보드 (배치·소스·번역·비용 모니터링) | P1-3, P2-1 |

**총 21 컨텍스트 단위** | MVP(Phase 1): P0 ~ P4-1 전체

---

## 실행 순서 (의존성 그래프)

```
P0-1 → P0-2 ─┬→ P1-1 → P1-2
              │         → P1-3 → P1-4
              │                → P1-5
              │
              └→ P2-1 ─┬→ P2-2 ─┐
                        → P2-3 ─┼→ P2-5 → P2-6 → P2-7
                        └→ P2-4 ─┘

P1-3 + P2-1 ──────────────────────────────→ P4-1

P1-3 → P3-1 → P3-2 ─┬→ P3-3 ─┐
                      └→ P3-4 ─┴→ P3-5 → P3-6
```

---

## 상세 명세

---

### P0-1 — 레포 구조 + Docker Compose + 환경변수

**목표**: 로컬 개발 환경을 한 번에 올릴 수 있는 기반 세팅

**생성 파일**
```
/
├── docker-compose.yml          # postgres, redis, meilisearch, api, worker, beat
├── docker-compose.dev.yml      # 볼륨 마운트, hot reload
├── .env.example                # 모든 환경변수 키 목록
├── .gitignore
├── backend/
│   ├── Dockerfile
│   └── pyproject.toml          # poetry 의존성 (fastapi, celery, anthropic, ...)
├── frontend/
│   └── package.json            # next 15, react, tailwind, ...
└── pipeline/                   # Celery 워커 (backend와 코드 공유)
    └── Dockerfile
```

**체크리스트**
- [ ] `docker-compose up`으로 postgres·redis·meilisearch 기동 확인
- [ ] `.env.example`에 모든 필수 키 주석 포함 (CLAUDE_API_KEY, GITHUB_TOKEN, OAuth 키 등)
- [ ] `backend/`와 `pipeline/`이 동일 Python 패키지를 공유하는 구조 확인

---

### P0-2 — DB 스키마 + Alembic 마이그레이션

**목표**: `docs/erd.md` 기반 전체 테이블을 마이그레이션 파일로 구현

**생성 파일**
```
backend/
├── alembic.ini
├── alembic/
│   └── versions/
│       └── 0001_initial_schema.py   # 전체 테이블 + 인덱스 + CHECK 제약
├── app/
│   └── models/
│       ├── card.py          # cards, card_tags SQLAlchemy 모델
│       ├── user.py          # users, user_likes, user_bookmarks
│       └── batch.py         # batch_logs, translation_logs, source_health
```

**체크리스트**
- [ ] `alembic upgrade head` 성공
- [ ] CHECK 제약 확인 (NEWS → key_points NOT NULL, TECHNIQUE → problem NOT NULL)
- [ ] UNIQUE 제약 확인 (user_likes, user_bookmarks)
- [ ] 인덱스 6개 생성 확인 (erd.md 인덱스 전략 참조)

---

### P1-1 — FastAPI 앱 골격

**목표**: 라우터·미들웨어·에러 핸들러·헬스체크 기반 구조

**생성 파일**
```
backend/app/
├── main.py                  # FastAPI 앱 인스턴스, 미들웨어, 라우터 등록
├── config.py                # Pydantic Settings (.env 로딩)
├── database.py              # SQLAlchemy async engine + session
├── redis.py                 # Redis 연결
├── exceptions.py            # 공통 에러 코드 + HTTPException 핸들러
├── routers/
│   └── health.py            # GET /health → {"status": "ok", db, redis 상태}
└── schemas/
    └── common.py            # ErrorResponse, PaginatedResponse
```

**체크리스트**
- [ ] `GET /health` → 200, DB·Redis 연결 상태 포함
- [ ] CORS 설정 (Next.js 개발 서버 허용)
- [ ] 에러 응답이 `{"error": {"code": ..., "message": ..., "status": ...}}` 형식
- [ ] `GET /docs` Swagger UI 접속 확인

---

### P1-2 — 인증 모듈 (OAuth + JWT)

**목표**: Google·GitHub OAuth 소셜 로그인 + JWT 발급·갱신

**생성 파일**
```
backend/app/
├── routers/auth.py          # /auth/{provider}, /auth/{provider}/callback, /auth/refresh, /auth/logout
├── services/auth.py         # OAuth 흐름, JWT 생성·검증
├── dependencies.py          # get_current_user (JWT 파싱), optional_user
└── schemas/auth.py          # TokenResponse, UserProfile
```

**체크리스트**
- [ ] Google OAuth 로그인 → JWT 발급 e2e 확인
- [ ] GitHub OAuth 로그인 → JWT 발급 e2e 확인
- [ ] 만료 토큰으로 보호된 엔드포인트 접근 시 401 반환
- [ ] `GET /me` → 로그인 사용자 프로필 반환

---

### P1-3 — 카드 피드 API

**목표**: 카드 조회·필터·커서 페이지네이션·Redis 캐싱

**생성 파일**
```
backend/app/
├── routers/cards.py         # GET /cards, GET /cards/{id}
├── services/cards.py        # 피드 조회 로직, 캐시 키 관리
└── schemas/cards.py         # CardNewsResponse, CardTechResponse, FeedResponse
```

**동작 명세**
- 쿼리 파라미터: `category`, `card_type`, `tags[]`, `difficulty`, `cursor`, `limit`
- 커서 페이지네이션: `published_at` 역순
- 캐시: Redis TTL 5분 (카테고리·타입·커서 조합 키)
- 비로그인 사용자: `is_liked`, `is_bookmarked` 필드 → `false`

**체크리스트**
- [ ] 카테고리·타입·태그 필터 조합 동작 확인
- [ ] 커서 기반 다음 페이지 조회 확인
- [ ] Redis 캐시 히트/미스 로깅 확인
- [ ] NEWS / TECHNIQUE 응답 스키마 분리 확인

---

### P1-4 — 좋아요·북마크 API + 추천 피드

**목표**: 좋아요·북마크 CRUD + Phase 1 규칙 기반 추천

**생성 파일**
```
backend/app/
├── routers/
│   ├── interactions.py      # POST/DELETE /cards/{id}/like, /cards/{id}/bookmark
│   ├── me.py                # GET /me/bookmarks
│   └── recommendations.py   # GET /cards/recommended
└── services/
    ├── interactions.py      # 좋아요·북마크 처리 + like_count 업데이트
    └── recommendations.py   # 카테고리·태그·card_type 빈도 집계 → 추천 피드
```

**추천 로직**
```
최근 30일 좋아요·북마크 이력
→ 카테고리·태그·card_type 빈도 집계
→ 80%: 상위 패턴 최신 카드
→ 20%: 미접촉 카테고리 인기 카드 (필터 버블 방지)
```

**체크리스트**
- [ ] 동일 사용자 중복 좋아요 시 409 반환
- [ ] 좋아요 추가/취소 시 `cards.like_count` 동기 업데이트
- [ ] `GET /me/bookmarks?category=CODING` 필터 동작
- [ ] 추천 피드 20% 다양성 보장 확인

---

### P1-5 — 검색 API + Meilisearch 연동

**목표**: 한국어 전문 검색 + 카드 인덱싱 파이프라인

**생성 파일**
```
backend/app/
├── routers/search.py        # GET /search?q=...&category=...&card_type=...
├── services/search.py       # Meilisearch 쿼리 래퍼
└── tasks/index_card.py      # 카드 저장 시 Meilisearch 인덱스 동기화 (이벤트 훅)
```

**Meilisearch 인덱스 설정**
- 검색 필드: `title`, `summary`, `problem`, `idea`, `tags`
- 필터 필드: `category`, `card_type`, `difficulty`
- 정렬 필드: `published_at`, `like_count`

**체크리스트**
- [ ] 한국어 쿼리 (`RAG 패턴`) 검색 결과 반환 확인
- [ ] 카드 INSERT 시 자동 인덱싱 확인
- [ ] `category` + `card_type` 복합 필터 동작 확인

---

### P2-1 — Celery·Beat 기반 + 배치 오케스트레이터 + 로깅

**목표**: 배치 실행 골격, 스케줄, batch_logs 기록

**생성 파일**
```
pipeline/
├── celery_app.py            # Celery 인스턴스, Redis 브로커 설정
├── beat_schedule.py         # Cron: 0 0,6,12,18 * * * (KST)
├── tasks/
│   └── orchestrate.py       # 배치 진입점: 소스 수집 → 필터 → AI → 발행 순서 조율
└── models/
    └── batch_log.py         # batch_logs INSERT / UPDATE 헬퍼
```

**체크리스트**
- [ ] `celery beat` 실행 시 KST 00/06/12/18시에 태스크 큐 발행 확인
- [ ] 배치 시작·완료·실패 시 `batch_logs` 레코드 생성 확인
- [ ] 배치 실패 시 15분 후 자동 재시도 (max_retries=2) 확인
- [ ] `--max-tasks-per-child=50` 워커 설정 확인

---

### P2-2 — 소스 어댑터 — 그룹 A (뉴스 RSS)

**목표**: RSS 소스 9개에서 직전 6시간분 아이템 수집

**생성 파일**
```
pipeline/adapters/
├── base.py                  # BaseAdapter 추상 클래스 (fetch() → List[RawItem])
└── rss.py                   # feedparser 기반 RSS 어댑터
pipeline/sources/
└── group_a.py               # RSS URL 9개 + 수집 태스크
```

**RawItem 스키마**
```python
@dataclass
class RawItem:
    url: str
    title: str
    content: str
    published_at: datetime
    source_name: str
    source_group: SourceGroup
    original_lang: str   # "en" | "ko"
```

**체크리스트**
- [ ] 9개 소스 각각 최소 1건 이상 수집 확인
- [ ] `published_at` 기준 6시간 이내 필터 동작 확인
- [ ] 소스 접속 실패 시 `source_health.consecutive_failures` 증가 확인
- [ ] Hacker News API 어댑터 별도 구현 (`/algolia` API 사용)

---

### P2-3 — 소스 어댑터 — 그룹 B-1 (GitHub Releases)

**목표**: 핵심 프레임워크 9개 릴리스 API 수집

**생성 파일**
```
pipeline/adapters/
└── github.py                # GitHub Releases API 어댑터 (토큰 인증)
pipeline/sources/
└── group_b.py               # B-1 리포 목록 + 수집 태스크
```

**필터 로직**
- `published_at` 직전 6시간 이내
- CHANGELOG 본문 300자 미만 → 자동 제외
- 403 응답 → `source_health` 기록 + 다음 배치 연기

**체크리스트**
- [ ] LangChain 최신 릴리스 수집 + CHANGELOG 본문 포함 확인
- [ ] 300자 미만 릴리스 제외 동작 확인
- [ ] Rate limit 헤더 파싱 + 잔여량 로깅 확인
- [ ] 404 응답 시 `source_health.enabled = false` 처리 확인

---

### P2-4 — 소스 어댑터 — 그룹 C-1 + D-1

**목표**: 엔지니어링 블로그 8개 + Substack 뉴스레터 4개 RSS 수집

**생성 파일**
```
pipeline/sources/
├── group_c.py               # C-1 기업 블로그 URL 목록 + RSS 어댑터 재사용
└── group_d.py               # D-1 Substack RSS URL 목록
```

**공통**: P2-2의 RSS 어댑터 재사용. 소스별 RSS URL만 추가.

**체크리스트**
- [ ] Anthropic Engineering 블로그 수집 확인
- [ ] Latent Space Substack 수집 확인
- [ ] 그룹 C·D 아이템에 `source_group = ENG_BLOG / NEWSLETTER` 올바르게 태깅 확인

---

### P2-5 — 중복 필터링

**목표**: URL 완전 일치 + 제목 TF-IDF 유사도 기반 중복 제거

**생성 파일**
```
pipeline/tasks/
└── deduplicate.py           # URL 해시 set 조회 + TF-IDF 유사도 계산
```

**로직**
1. URL SHA-256 해시 → `cards.source_url` 기 존재하면 제거
2. 배치 내 아이템 간 제목 TF-IDF 유사도 행렬 계산
3. 유사도 ≥ 0.9 클러스터 → 가장 긴 content를 가진 1건만 유지
4. 그룹 A·C·D가 동일 GitHub Release URL을 다룬 경우 → source_url 기준 1건 유지

**체크리스트**
- [ ] 동일 URL 재수집 시 제외 확인
- [ ] 유사 제목 2건 → 1건만 통과 확인
- [ ] `batch_logs.deduplicated_count` 업데이트 확인

---

### P2-6 — Claude API — NEWS 요약·번역·분류

**목표**: NEWS 카드용 Claude API 호출 체인 구현

**생성 파일**
```
pipeline/tasks/
└── ai_process_news.py       # LangChain 체인: 타입 판정 → 요약 → 번역 → 분류
pipeline/prompts/
├── classify_type.py         # NEWS / TECHNIQUE 판정 프롬프트
├── summarize_news.py        # What/Why/Impact 3단 요약 프롬프트
└── translate.py             # 기술 도메인 한국어 번역 프롬프트
```

**LangChain 체인 순서**
```
원문 → [타입 판정] → NEWS 분기
     → [요약 생성] (What/Why/Impact, 3~5문장)
     → [카테고리·태그·난이도 부여]
     → [영문이면 한국어 번역]
     → CardData 반환
```

**체크리스트**
- [ ] TechCrunch 기사 → NEWS 카드 데이터 생성 확인
- [ ] 한국어 원문은 번역 스킵 확인
- [ ] 판정 불확실 항목 → NEWS fallback 확인
- [ ] `api_tokens_used` + `api_cost_usd` 집계 확인

---

### P2-7 — Claude API — TECHNIQUE 요약·번역 + 역번역 검증

**목표**: TECHNIQUE 카드 처리 체인 + 번역 품질 검증

**생성 파일**
```
pipeline/tasks/
└── ai_process_technique.py  # TECHNIQUE 전용 체인
pipeline/prompts/
└── summarize_technique.py   # 문제/아이디어/코드/주의점 4단 프롬프트
pipeline/tasks/
└── verify_translation.py    # 역번역 + sentence-transformers 유사도
```

**역번역 검증 흐름**
```python
ko_summary → back_translate(ko→en) → cosine_similarity(original_en, back_en)
           [Claude API]             [paraphrase-multilingual-MiniLM-L12-v2]
≥ 0.85 → pass
< 0.85 → retry (max 3)
3회 실패 → manual_review_queue
```

**체크리스트**
- [ ] LangChain GitHub 릴리스 → TECHNIQUE 카드 4단 구조 생성 확인
- [ ] `code_snippet` 원본 추출 확인 (LLM 생성 코드 없음)
- [ ] 역번역 유사도 0.85 미만 시 재번역 트리거 확인
- [ ] sentence-transformers 모델 워커 시작 시 사전 로딩 확인
- [ ] `translation_logs` 테이블 기록 확인

---

### P3-1 — Next.js 15 프로젝트 + 레이아웃 + API 클라이언트

**목표**: 프론트엔드 기반 구조, 글로벌 레이아웃, API 클라이언트

**생성 파일**
```
frontend/
├── app/
│   ├── layout.tsx           # 글로벌 레이아웃 (헤더, 탭 네비게이션)
│   ├── page.tsx             # 메인 피드 (/ 경로)
│   └── cards/[id]/page.tsx  # 카드 상세 (SSR, OG 메타 포함)
├── lib/
│   └── api.ts               # Fetch 래퍼 (baseURL, JWT 헤더, 에러 처리)
├── stores/
│   └── auth.ts              # Zustand 인증 상태 (token, user)
└── tailwind.config.ts
```

**체크리스트**
- [ ] `npm run dev` 정상 기동 확인
- [ ] API 클라이언트가 `.env.local`의 `NEXT_PUBLIC_API_URL` 읽기 확인
- [ ] 헤더·탭 네비게이션 렌더링 확인
- [ ] `cards/[id]` SSR 메타 태그 (`og:title`, `og:description`) 확인

---

### P3-2 — 카드 피드 페이지

**목표**: 무한 스크롤 피드 + 카테고리 탭 + 타입 필터

**생성 파일**
```
frontend/app/
└── (feed)/
    ├── page.tsx             # 피드 페이지
    └── components/
        ├── CategoryTabs.tsx     # [전체][프로그래밍][디자인][일반] 탭
        ├── TypeFilter.tsx       # [전체][📰 뉴스][⚙️ 기법] 토글
        ├── TagChips.tsx         # 태그 칩 필터
        └── InfiniteCardList.tsx # IntersectionObserver 기반 무한 스크롤
```

**체크리스트**
- [ ] 탭 전환 시 URL 쿼리 파라미터 업데이트 (`?category=CODING`)
- [ ] 스크롤 끝 도달 시 다음 페이지 자동 로드 확인
- [ ] 로딩 스켈레톤 표시 확인
- [ ] 결과 없음 빈 상태 UI 확인

---

### P3-3 — NEWS 카드 컴포넌트

**목표**: NEWS 카드 UI (미리보기 + 상세 펼치기)

**생성 파일**
```
frontend/components/cards/
├── NewsCard.tsx             # 카드 미리보기 (제목, 요약 2줄, 태그, 날짜)
├── NewsCardExpanded.tsx     # 펼침 상태 (What/Why/Impact 전체, 원본 링크)
└── CardBadges.tsx           # 타입 뱃지(📰), 카테고리 뱃지, 난이도 별
```

**디자인 기준**
- 카테고리 뱃지 색: 프로그래밍(파란), 디자인(보라), 일반(초록)
- 카드 탭 → 펼침 애니메이션 (Framer Motion 또는 CSS transition)

**체크리스트**
- [ ] 카드 탭 → 상세 펼치기 토글 동작 확인
- [ ] 원본 URL 링크 새 탭 열기 확인
- [ ] 타입·카테고리·난이도 뱃지 시각 확인

---

### P3-4 — TECHNIQUE 카드 컴포넌트 (Shiki 코드 블록)

**목표**: TECHNIQUE 카드 UI + 코드 하이라이팅

**생성 파일**
```
frontend/components/cards/
├── TechniqueCard.tsx        # 카드 미리보기 (기법명, 문제 요약 2줄)
├── TechniqueCardExpanded.tsx # 펼침: 문제/아이디어/코드/주의점 4단
└── CodeBlock.tsx            # Shiki 기반 코드 하이라이터 (SSR)
```

**체크리스트**
- [ ] 4단 구조 (문제·아이디어·코드·주의점) 순서대로 렌더링 확인
- [ ] 코드 블록 언어 자동 감지 + 하이라이팅 확인
- [ ] 코드 없는 카드에서 코드 섹션 숨김 처리 확인
- [ ] ⚙️ 타입 뱃지 + 선행지식 표시 확인

---

### P3-5 — 인증 UI + 소셜 로그인 + 좋아요·북마크 인터랙션

**목표**: 로그인 모달, 인증 상태 관리, 인터랙션 버튼

**생성 파일**
```
frontend/components/
├── AuthModal.tsx            # 비로그인 접근 시 소셜 로그인 유도 모달
├── SocialLoginButtons.tsx   # Google / GitHub 버튼
└── cards/
    └── CardActions.tsx      # ❤️ 좋아요 / 🔖 북마크 / 🔗 공유 버튼
```

**동작 명세**
- 비로그인 상태에서 좋아요·북마크 클릭 → 로그인 모달 표시
- 로그인 후 낙관적 업데이트 (클릭 즉시 UI 반영, 실패 시 롤백)

**체크리스트**
- [ ] Google OAuth 로그인 플로우 e2e 확인
- [ ] 좋아요 클릭 → 서버 응답 전 UI 즉시 반영 + 실패 롤백 확인
- [ ] 북마크 후 `/me/bookmarks` 페이지에서 조회 확인
- [ ] JWT 저장 (httpOnly 쿠키 또는 메모리) 방식 결정 및 구현

---

### P3-6 — SEO + OG 이미지 + 공유 기능 + PWA

**목표**: 검색 노출 + SNS 공유 + PWA 기본 설정

**생성 파일**
```
frontend/
├── app/cards/[id]/
│   └── opengraph-image.tsx  # Next.js 동적 OG 이미지 생성
├── app/sitemap.ts           # 동적 사이트맵 (최근 1000개 카드)
├── app/robots.ts
└── public/
    └── manifest.json        # PWA 매니페스트
```

**OG 이미지 스펙**: 1200×630, 카드 제목·타입 뱃지·카테고리 포함

**체크리스트**
- [ ] `aipulse.kr/cards/{id}` → OG 이미지 URL 반환 확인
- [ ] Twitter Card / OG 태그 미리보기 확인
- [ ] JSON-LD Article 스키마 삽입 확인
- [ ] `/sitemap.xml` 접근 가능 확인
- [ ] 카카오톡 공유 버튼 동작 확인

---

### P4-1 — 관리 대시보드

**목표**: 배치·소스·번역·비용 현황을 한눈에 보는 어드민 페이지

**생성 파일**
```
frontend/app/admin/
├── layout.tsx               # 어드민 레이아웃 (관리자 인증 가드)
├── page.tsx                 # 대시보드 홈 (주요 지표 요약)
├── batches/page.tsx         # 배치 실행 이력 테이블
├── sources/page.tsx         # 소스 헬스체크 + 활성화/비활성화 토글
├── translation/page.tsx     # 번역 품질 + 수동 검토 큐
└── costs/page.tsx           # Claude API 토큰·비용 일/월 추이 차트
```

**주요 지표 (대시보드 홈)**
- 오늘 발행: NEWS N장 / TECHNIQUE N장
- 배치 성공률 (최근 7일)
- 번역 검증 통과율
- 이번 달 Claude API 비용 ($N / 예산 $N)
- 소스 이상 경보 (연속 실패 소스 목록)

**체크리스트**
- [ ] 어드민 라우트 비인가 접근 시 리다이렉트 확인
- [ ] 배치 로그 테이블: 소스 그룹별 수집량·중복 제거율 표시
- [ ] 소스 헬스: 연속 실패 소스 빨간색 경고 표시
- [ ] 수동 검토 큐: 카드 내용 확인 + 통과/삭제 액션

---

## 이후 단계 (Phase 2 이후)

| Phase | 작업 | 선행 조건 |
|---|---|---|
| P5-1 | React Native (Expo) 기반 + 탭 네비게이션 + 카드 피드 | MVP 완성 후 |
| P5-2 | 모바일 카드 컴포넌트 + 스와이프 제스처 (좌=북마크, 우=스킵) | P5-1 |
| P5-3 | 푸시 알림 (Expo Notifications) + 카카오 로그인 | P5-2 |
| P5-4 | 소스 그룹 B-2 (Trending) + B-3 (Awesome) + C-2 (개인 블로그) 어댑터 | P2-4 |
| P5-5 | 소스 그룹 D-2 (IMAP 이메일) 어댑터 | P5-4 |
| P6-1 | 협업 필터링 추천 (DAU 1만 이상 시) | P1-4 |
| P6-2 | Elasticsearch 전환 + nori 한국어 형태소 분석 | P1-5 |
