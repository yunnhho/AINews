# AI Pulse

> AI/LLM 뉴스·기법을 자동 수집하고, Claude로 요약·번역·분류해 카드 형태로 제공하는 큐레이션 플랫폼

매일 4회(KST 00/06/12/18시) RSS·GitHub·엔지니어링 블로그·뉴스레터에서 AI 관련 콘텐츠를 수집한 뒤, 중복을 제거하고 Claude API로 **요약·한국어 번역·분류**를 거쳐 `NEWS`/`TECHNIQUE` 두 종류의 카드로 발행합니다. 웹(Next.js)·모바일(React Native)·관리자 대시보드를 모두 제공합니다.

---

## 목차

- [핵심 기능](#핵심-기능)
- [기술 스택](#기술-스택)
- [시스템 아키텍처](#시스템-아키텍처)
- [데이터 모델](#데이터-모델)
- [배치 파이프라인](#배치-파이프라인)
- [빠른 시작](#빠른-시작)
- [프로젝트 구조](#프로젝트-구조)
- [Troubleshooting](#troubleshooting)
- [설계 의사결정](#설계-의사결정)

---

## 핵심 기능

| 영역 | 기능 |
|---|---|
| **콘텐츠 수집** | 4개 소스 그룹(뉴스 RSS·GitHub·엔지니어링 블로그·뉴스레터)에서 6시간 단위 병렬 수집. GitHub은 Releases·토픽 트렌딩(claude-md 등)·awesome-* README diff·큐레이션 CLAUDE.md까지 확장 |
| **중복 제거** | URL SHA-256 완전 일치 + 제목 TF-IDF 유사도(≥0.9) 클러스터링 |
| **AI 처리** | Claude API로 타입 판정 → 요약(What/Why/Impact) → 한국어 번역 → 카테고리·태그·난이도 부여 |
| **번역 품질 검증** | 역번역 후 `sentence-transformers` 코사인 유사도 ≥0.85만 통과, 미달 시 재시도·수동 검토 큐 이관 |
| **피드 API** | 커서 페이지네이션 + 카테고리/타입/태그 필터 + Redis 캐싱(TTL 5분) |
| **개인화 추천** | 규칙 기반(80/20 다양성) → 협업 필터링(implicit ALS) 단계적 고도화, cold start 폴백 |
| **한국어 검색** | Elasticsearch + nori 형태소 분석기 (Meilisearch에서 마이그레이션) |
| **인증** | Google·GitHub·Kakao OAuth + JWT (만료 토큰 자동 정리·재로그인 유도) |
| **보안** | 보안 헤더(CSP·HSTS·X-Frame-Options) + Redis 기반 IP 레이트리밋(fail-open) + 운영 시크릿/호스트 가드 |
| **관리자 대시보드** | 배치 이력·소스 헬스체크·번역 품질·Claude API 비용 모니터링 + Slack/이메일 경보 |
| **모바일** | Expo 앱 — 스와이프 제스처(좌=북마크, 우=스킵) + Expo 푸시 알림 |

카드는 반드시 **`NEWS`**(What/Why/Impact 요약 + 핵심 불릿)와 **`TECHNIQUE`**(문제/아이디어/코드/주의점 4단 구조) 두 가지로만 구분합니다. 코드 스니펫은 LLM이 생성하지 않고 **원본에서 추출만** 하며, 원본 전문은 저장하지 않고 항상 원본 URL을 노출합니다.

---

## 기술 스택

### Backend
- **FastAPI** 0.115 (Python 3.12, async)
- **SQLAlchemy** 2.0 (async) + **asyncpg** + **Alembic** 마이그레이션
- **PostgreSQL** 16 — 단일 `cards` 테이블 + 타입별 nullable 컬럼 구조
- **Redis** 7 — 피드/추천 캐시 + Celery 브로커
- **Elasticsearch** 8.17 (nori 한국어 형태소 분석기)
- **Anthropic SDK** — 타입별 프롬프트 분리(요약·번역·분류)
- **sentence-transformers** 3.3 (`paraphrase-multilingual-MiniLM-L12-v2`) — 번역 검증
- **scikit-learn** — TF-IDF 중복 제거, implicit ALS 추천
- 인증: **Authlib**(OAuth) + **python-jose**(JWT)

### Pipeline (배치)
- **Celery** 5.4 + **Celery Beat** — KST 0/6/12/18시 스케줄
- **feedparser** — RSS/Substack, **httpx** — GitHub REST API, **BeautifulSoup** — Trending 스크래핑, **IMAP** — 이메일 뉴스레터

### Frontend (Web)
- **Next.js** 15 (App Router, SSR/SSG) + **React** 19
- **Tailwind CSS** 3.4 + **Framer Motion**(애니메이션) + **Shiki**(코드 하이라이팅)
- **Zustand** — 인증 상태 관리
- 에디토리얼(신문/매거진) 톤 디자인 + **Pretendard** 본문 폰트 + IBM Plex Mono 라벨
- SEO: 동적 OG 이미지, sitemap, JSON-LD, PWA manifest
- 보안: `next.config` 보안 헤더 + CSP

### Mobile
- **Expo** 52 + **Expo Router** 4 + **React Native** 0.76
- **NativeWind** 4 (Tailwind), **Reanimated** + **Gesture Handler**(스와이프), **Expo Notifications**(푸시)

### Infra / DevOps
- **Docker Compose** — 로컬 전체 스택(postgres·redis·elasticsearch·api·worker·beat)
- **GitHub Actions** — CI(테스트) + 배포
- **AWS ECS Fargate** — API 서버·배치 워커 독립 스케일링
- 모니터링: Sentry + Prometheus + Grafana

### 품질 도구
- **ruff**(lint) + **mypy**(타입) + **pytest** / **pytest-asyncio**

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  클라이언트 계층                                              │
│  Next.js (웹/SSR)   React Native (iOS/Android)               │
└───────────────────────────┬─────────────────────────────────┘
                            ▼  API Gateway
┌─────────────────────────────────────────────────────────────┐
│  서비스 계층                                                  │
│  ┌──────────────── FastAPI Server ─────────────────┐         │
│  │  인증 / 피드 / 추천 / 검색 / 관리자              │         │
│  │     │            │              │                │         │
│  │  PostgreSQL    Redis      Elasticsearch          │         │
│  │  (메인 DB)   (캐시/큐)    (한국어 검색)          │         │
│  └──────────────────────────────────────────────────┘        │
│                                                               │
│  ┌──────── 배치 파이프라인 (Celery + Beat) ─────────┐         │
│  │  Cron: 0 0,6,12,18 * * * (KST)                  │         │
│  │  ① 소스별 병렬 수집                              │         │
│  │  ② 중복·유사 필터링 (URL + TF-IDF 0.9)           │         │
│  │  ③ 카드 타입 자동 판정 (NEWS / TECHNIQUE)        │         │
│  │  ④ Claude API 호출 (타입별 프롬프트)             │         │
│  │  ⑤ 번역 검증 (역번역 + 유사도 ≥ 0.85)            │         │
│  │  ⑥ 카드 생성 → DB 저장 → 캐시·인덱스 갱신        │         │
│  │  ⑦ 배치 로그 + 비용 집계 + 소스 경보             │         │
│  └──────────────────────────────────────────────────┘        │
│                                                               │
│  외부: Claude API · RSS · GitHub API · OAuth · CDN           │
└─────────────────────────────────────────────────────────────┘
```

**요청 경로**: `사용자 → CDN → Next.js(SSR) → FastAPI → Redis 캐시(히트) / PostgreSQL(미스) / Elasticsearch(검색)`

상세: [docs/architecture.md](docs/architecture.md)

---

## 데이터 모델

단일 `cards` 테이블에 카드 타입별 nullable 컬럼을 두고, **CHECK 제약**으로 타입 무결성을 보장합니다.

```sql
ALTER TABLE cards ADD CONSTRAINT card_type_fields CHECK (
  (card_type = 'NEWS'      AND key_points IS NOT NULL AND problem IS NULL)
  OR
  (card_type = 'TECHNIQUE' AND problem IS NOT NULL AND idea IS NOT NULL)
);
```

| 테이블 | 역할 |
|---|---|
| `cards` / `tags` / `card_tags` | 카드 본문 + 태그 (다대다) |
| `users` / `user_likes` / `user_bookmarks` | 사용자 + 상호작용 (UNIQUE 제약으로 중복 방지) |
| `batch_logs` | 배치별 수집량·중복 제거율·발행 타입·토큰·비용 집계 |
| `translation_logs` | 원문/번역/역번역 + 유사도 점수 + 통과 여부 |
| `source_health` | 소스별 연속 실패 카운트·활성화 상태 (경보 판정 근거) |
| `user_devices` | Expo 푸시 디바이스 토큰 |

상세: [docs/erd.md](docs/erd.md)

---

## 배치 파이프라인

```
원문 → [타입 판정] → NEWS 분기   → 요약(What/Why/Impact) → 분류 → (영문이면) 번역
                   → TECH 분기   → 4단 요약(문제/아이디어/코드/주의점) → 번역 → 역번역 검증
```

**번역 검증 흐름** (TECHNIQUE 카드)

```python
ko_summary → back_translate(ko→en) → cosine_similarity(original_en, back_en)
           [Claude API]             [paraphrase-multilingual-MiniLM-L12-v2]
≥ 0.85 → pass
< 0.85 → retry (max 3) → 3회 실패 시 manual_review_queue
```

소스 그룹은 **A(뉴스 RSS) → B(GitHub) → C(엔지니어링 블로그) → D(뉴스레터)** 순으로 도입했습니다. 상세: [docs/pipeline.md](docs/pipeline.md) · [docs/content-sources.md](docs/content-sources.md)

---

## 빠른 시작

### 사전 요구사항
- Docker / Docker Compose
- (로컬 개발 시) Python 3.12 + Poetry, Node.js 20+

### 1. 환경변수 설정

```bash
cp .env.example .env
# CLAUDE_API_KEY, GITHUB_TOKEN, OAuth 키 등을 채운다 (API_KEYS.md 참고)
```

### 2. 전체 스택 기동

```bash
docker compose up -d           # postgres · redis · elasticsearch · api · worker · beat
docker compose exec api alembic upgrade head   # DB 마이그레이션
docker compose exec api python -m app.es.setup # Elasticsearch 인덱스 생성 + 재인덱싱
```

- API: http://localhost:8000 · Swagger: http://localhost:8000/docs · Health: `GET /health`

### 3. 웹 프론트엔드

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000  (.env.local에 NEXT_PUBLIC_API_URL 설정)
```

### 4. 모바일 앱

```bash
cd mobile
npm install
npx expo start   # EXPO_PUBLIC_API_URL 설정 후 iOS/Android 시뮬레이터
```

> 핫 리로드 개발용으로는 `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` 사용.

---

## 프로젝트 구조

```
AINews/
├── backend/              # FastAPI 서버
│   ├── app/
│   │   ├── routers/      # auth, cards, interactions, me, recommendations, search, admin, alerts, push, health
│   │   ├── middleware.py # 보안 헤더 + 레이트리밋
│   │   ├── services/     # 비즈니스 로직 레이어
│   │   ├── models/       # SQLAlchemy 모델
│   │   ├── schemas/      # Pydantic 스키마
│   │   └── tasks/        # index_card, build_cf_model
│   ├── alembic/          # 마이그레이션
│   └── es/               # Elasticsearch 매핑(nori) + setup 스크립트
├── pipeline/             # Celery 배치 워커
│   └── pipeline/
│       ├── adapters/     # rss, github, github_trending, hackernews, imap
│       ├── sources/      # group_a ~ group_d2 (소스 그룹별)
│       ├── filters/      # dedup (URL + TF-IDF)
│       ├── ai/           # news/technique processor, prompts, backtranslate, publisher
│       └── tasks/        # orchestrate, check_source_health, send_push, train_cf
├── frontend/             # Next.js 15 웹
│   ├── app/              # (feed), cards/[id], admin/*, auth/callback
│   ├── components/cards/ # NewsCard, TechniqueCard, CodeBlock 등
│   └── lib/              # api 클라이언트
├── mobile/               # Expo (React Native)
├── docs/                 # erd, architecture, pipeline, api-design, content-sources, phases, sessions
├── docker-compose.yml
└── CLAUDE.md             # 프로젝트 대규칙
```

---

## Troubleshooting

개발 과정에서 마주친 핵심 문제들과 해결 과정입니다.

### 1. 검색 엔진 한국어 형태소 분석 한계 (Meilisearch → Elasticsearch)

- **문제**: 초기에는 가벼운 Meilisearch를 도입했으나, `RAG 패턴` 같은 한국어 복합 검색에서 형태소 단위 매칭이 약해 `RAG`와 `패턴`을 별도 토큰으로 처리하지 못했고, 조사가 붙은 단어(`임베딩을`, `임베딩이`)가 서로 다른 토큰으로 인식되어 재현율이 떨어졌다.
- **해결**: Elasticsearch 8.17로 전환하고 **nori 한국어 형태소 분석기**(`nori_tokenizer` + `nori_part_of_speech` 필터)를 커스텀 `korean` 분석기로 등록했다. nori 플러그인을 포함한 ES 이미지를 직접 빌드(`backend/es/Dockerfile`)하고, `es/setup.py`로 인덱스 생성 후 기존 카드를 전량 재인덱싱했다. `services/search.py`와 `tasks/index_card.py`를 ES 클라이언트로 교체한 뒤 docker-compose에서 Meilisearch 서비스를 제거했다.
- **결과**: 조사·어미가 정규화되어 한국어 검색 재현율이 크게 향상됐고, `title`/`summary`는 형태소 분석, `tags`/`category`는 keyword로 분리해 정확한 필터링과 자연어 검색을 동시에 만족시켰다.

### 2. AI 번역 품질을 사람 검수 없이 보장하기

- **문제**: Claude로 영문 기술 콘텐츠를 한국어로 번역할 때, 문법적으로는 자연스러우나 기술 용어가 누락·왜곡되는 경우(예: "context window"를 일반어로 의역)를 자동으로 걸러낼 방법이 없었다. 사람이 전수 검수하면 배치 파이프라인이 의미가 없어진다.
- **해결**: **역번역(back-translation) + 의미 유사도** 검증 루프를 도입했다. 번역된 한국어를 다시 영어로 역번역(Claude)한 뒤, 원문 영어와 역번역 영어를 `sentence-transformers`의 `paraphrase-multilingual-MiniLM-L12-v2`로 임베딩해 **코사인 유사도**를 계산한다. 0.85 이상만 통과시키고, 미달 시 최대 3회 재번역, 그래도 실패하면 `manual_review_queue`로 이관해 관리자 대시보드에서만 검토하도록 했다. 검증 모델은 매 카드마다 재로딩하지 않도록 **워커 시작 시 사전 로딩**했다.
- **결과**: 번역 비용 0(로컬 임베딩 모델)으로 의미 왜곡 카드를 자동 차단했고, 사람의 개입을 통과율 미달 케이스(소수)로만 한정해 무인 배치 파이프라인을 유지했다. `translation_logs`에 유사도 점수를 적재해 관리자 페이지에서 통과율 추이를 모니터링한다.

### 3. 여러 소스가 같은 릴리스를 다룰 때 카드 중복 발행

- **문제**: 동일한 LLM 프레임워크 릴리스를 뉴스 RSS(그룹 A)·엔지니어링 블로그(C)·뉴스레터(D)가 동시에 다루면, URL이 달라 단순 URL 비교만으로는 거의 같은 내용의 카드가 여러 장 발행됐다.
- **해결**: 2단계 중복 필터를 구현했다(`filters/dedup.py`). ① 수집 URL을 SHA-256 해시해 `cards.source_url` 기존 카드와 완전 일치 제거, ② 배치 내 아이템 간 **제목 TF-IDF 유사도 행렬**을 계산해 0.9 이상 클러스터는 본문(content)이 가장 긴 1건만 유지. 그룹 A·C·D가 동일 GitHub Release URL을 참조한 경우는 `source_url` 기준으로 1건만 남겼다.
- **결과**: 동일 주제 중복 카드가 제거되어 피드 품질이 개선됐고, `batch_logs.deduplicated_count`로 중복 제거율을 배치별 추적할 수 있게 됐다.

### 4. 추천 cold start — 신규 사용자에게 빈 피드

- **문제**: 협업 필터링(implicit ALS) 추천은 사용자-카드 상호작용 행렬이 필요한데, 가입 직후 좋아요·북마크 이력이 없는 사용자에게는 추천을 만들 수 없어 빈 피드가 노출됐다.
- **해결**: 2단 폴백 구조로 설계했다. 상호작용이 충분한 사용자는 ALS 모델(`factors=64`, Redis에 직렬화 저장)로 추천하고, **이력이 5건 미만인 cold start 사용자는 규칙 기반 추천**(최근 30일 카테고리·태그 빈도 집계, 80% 선호 패턴 + 20% 미접촉 카테고리 인기 카드)으로 폴백한다. ALS 모델은 일 1회 Celery 태스크로 재학습한다.
- **결과**: 신규 사용자도 첫 방문부터 의미 있는 피드를 받고, 20% 다양성 비율로 필터 버블을 완화했다. 이력이 쌓이면 자연스럽게 CF 추천으로 전환된다.

### 5. 배치 워커 메모리 누수와 소스 장애 전파

- **문제**: 장시간 가동되는 Celery 워커에서 sentence-transformers 모델과 HTTP 세션이 누적돼 메모리가 증가했고, 일부 소스(GitHub 403, 블로그 다운)의 장애가 배치 전체 실패로 번졌다.
- **해결**: 워커에 `--max-tasks-per-child=50`을 설정해 일정 태스크 처리 후 프로세스를 재생성하도록 했다. 소스 어댑터는 개별 실패를 격리해 `source_health.consecutive_failures`만 증가시키고 나머지 소스 수집은 계속 진행하도록 했으며, **연속 실패 3회 이상이면 Slack·이메일 경보**(쿨다운 1시간)를 발송하고 해당 소스를 자동 비활성화한다. 배치 실패 시 15분 후 자동 재시도(`max_retries=2`).
- **결과**: 장기 가동 메모리 사용량이 안정화됐고, 단일 소스 장애가 배치 전체를 중단시키지 않게 됐다. 관리자 대시보드의 소스 헬스 화면에서 이상 소스를 즉시 식별할 수 있다.

---

## 설계 의사결정

- **단일 `cards` 테이블 + nullable 컬럼**: NEWS/TECHNIQUE를 별도 테이블로 분리하지 않고 CHECK 제약으로 무결성을 보장 — 피드 조회 시 타입 혼합 정렬·페이지네이션이 단순해진다.
- **커서 페이지네이션**: `published_at` 역순 커서 방식으로 무한 스크롤 중 새 카드가 발행돼도 페이지 밀림(offset drift)이 없다.
- **코드 스니펫 원본 추출만**: LLM 환각 코드 방지를 위해 TECHNIQUE 카드의 코드는 생성하지 않고 원본에서 추출(최대 15줄)만 한다.
- **원본 전문 미저장**: 저작권 이슈를 피하기 위해 전문을 저장하지 않고 요약 + 원본 URL만 노출한다.
- **단계적 고도화**: 검색(Meilisearch→ES)·추천(규칙→CF)·소스(A→D) 모두 MVP를 먼저 띄우고 트래픽에 따라 교체하는 전략을 택했다.

상세 API 설계: [docs/api-design.md](docs/api-design.md) · 작업 단위 로드맵: [docs/phases.md](docs/phases.md)

---

## 라이선스

본 프로젝트는 포트폴리오 목적으로 작성되었습니다.
