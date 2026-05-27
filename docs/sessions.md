# AI Pulse — 8-Session Sprint Plan

> **세션 간 인수인계 규칙**  
> 각 세션 작업 완료 후, 다음 세션에 꼭 전달할 내용이 있으면  
> **다음 세션 문서의 가장 위에 3-40자 이내로 추가**할 것.  
> 전달 내용 없으면 추가하지 않음.

---

## 전체 로드맵

| 세션 | Phase | 테마 | 작업량 |
|---|---|---|---|
| **S1** | P1-4 + P1-5 | 백엔드 API 완성 | ★★★ |
| **S2** | P4-2 + P4-3 | Admin 백엔드 완성 | ★★★ |
| **S3** | P5-1 | 모바일 기반 (Expo) | ★★★ |
| **S4** | P5-2 | 모바일 카드 UI | ★★☆ |
| **S5** | P5-3 | 모바일 확장 (알림·카카오) | ★★★ |
| **S6** | P5-4 + P5-5 | 파이프라인 소스 확장 | ★★☆ |
| **S7** | P6-1 | 협업 필터링 추천 | ★★★ |
| **S8** | P6-2 | Elasticsearch 전환 | ★★★ |

**묶음 근거**
- S1: 둘 다 "누락된 백엔드 피처 완성" — 독립적이지만 같은 레이어
- S2: 둘 다 admin 도메인 — Admin API가 있어야 알림 조건 판정도 완성
- S3: Expo 신규 프로젝트 단독 — 새 기술 스택 시작은 집중 필요
- S4: 카드 UI만 집중 — 컴포넌트 수가 많아 단독 세션이 안전
- S5: 모바일+백엔드 모두 건드리는 복잡 작업 — 한 세션에 완결
- S6: 어댑터 패턴 동일, 모두 pipeline 도메인 — B2/B3/C2/D2 일괄 처리
- S7/S8: 각각 독립 고난도 피처 — 분리 필수

---

## Session 1 — P1-4 + P1-5: 백엔드 API 완성

### P1-4: 좋아요·북마크 + 추천 피드

**생성 파일**
```
backend/app/
├── routers/
│   ├── interactions.py      # POST/DELETE /cards/{id}/like, /cards/{id}/bookmark
│   ├── me.py                # GET /me/bookmarks?category=
│   └── recommendations.py   # GET /cards/recommended
└── services/
    ├── interactions.py      # like_count 동기 업데이트 포함
    └── recommendations.py   # 최근 30일 이력 → 80/20 추천
```

**추천 로직**
```
최근 30일 좋아요·북마크 이력
→ 카테고리·태그·card_type 빈도 집계
→ 80%: 상위 패턴 최신 카드
→ 20%: 미접촉 카테고리 인기 카드 (필터 버블 방지)
```

**체크리스트 — P1-4**
- [ ] 동일 사용자 중복 좋아요 → 409 반환
- [ ] 좋아요 추가/취소 시 `cards.like_count` 동기 업데이트
- [ ] `GET /me/bookmarks?category=CODING` 필터 동작
- [ ] 추천 피드 20% 다양성 보장 확인

---

### P1-5: 검색 API + Meilisearch 인덱싱

**생성 파일**
```
backend/app/
├── routers/search.py        # GET /search?q=&category=&card_type=&difficulty=
├── services/search.py       # async Meilisearch 쿼리 래퍼
└── tasks/index_card.py      # 카드 INSERT 후 자동 인덱싱 이벤트 훅
```

**Meilisearch 인덱스 설정**
- 검색 필드: `title`, `summary`, `problem`, `idea`, `tags`
- 필터 필드: `category`, `card_type`, `difficulty`
- 정렬 필드: `published_at`, `like_count`

**체크리스트 — P1-5**
- [ ] 한국어 쿼리 (`RAG 패턴`) 검색 결과 반환 확인
- [ ] 카드 INSERT 시 자동 인덱싱 확인
- [ ] `category` + `card_type` 복합 필터 동작
- [ ] docker-compose에 Meilisearch 서비스 존재 확인 (없으면 추가)
- [ ] `MEILISEARCH_URL`, `MEILISEARCH_KEY` env .env.example 반영

**세션 완료 후**
- `backend/app/main.py`에 interactions/me/recommendations/search 라우터 모두 등록 확인

---

<!-- S1→S2: 검색 엔진이 S8에서 Elasticsearch 8.17로 전환됨 (meilisearch 제거) -->

## Session 2 — P4-2 + P4-3: Admin 백엔드 완성

### P4-2: Admin API 엔드포인트 5개

**생성 파일**
```
backend/app/
├── routers/admin.py         # 5개 엔드포인트 + 관리자 권한 의존성
└── services/admin.py        # 각 엔드포인트 DB 쿼리 로직
```

**엔드포인트 명세**

| 경로 | 반환 |
|---|---|
| `GET /admin/metrics` | 오늘 발행수(NEWS/TECH), 배치 성공률(7일), 번역 통과율, 이달 비용 |
| `GET /admin/batches` | batch_logs 최근 50건 (소스 그룹별 수집량·중복 제거율) |
| `GET /admin/sources/health` | source_health 전체 (연속 실패 소스 포함) |
| `GET /admin/translation-queue` | manual_review 상태 카드 목록 |
| `GET /admin/costs/daily` | 최근 30일 일별 api_cost_usd + 토큰 집계 |
| `PATCH /admin/translation-queue/{id}` | 수동 검토 통과/삭제 처리 |

**체크리스트 — P4-2**
- [ ] 관리자 권한 미보유 → 403 반환
- [ ] 응답 스키마가 `frontend/lib/admin-api.ts` 타입과 일치
- [ ] `/admin/sources/health`: 연속 실패 3회 이상 → `status: "critical"` 표시

---

### P4-3: 알림 시스템 (소스 이상 경보)

**생성 파일**
```
backend/app/
├── services/alerting.py     # 경보 조건 판정 + Slack 웹훅 + 이메일 발송
└── routers/alerts.py        # GET /admin/alerts (이력), POST /admin/alerts/test

pipeline/tasks/
└── check_source_health.py   # 배치 완료 후 소스 상태 점검 태스크
```

**경보 조건**
- `source_health.consecutive_failures >= 3` → Slack + 이메일 즉시 발송
- 배치 전체 수집 0건 → 즉시 발송
- 번역 통과율 < 70% (최근 100건) → 일 1회 발송

**추가 환경변수** (`.env.example`에 추가)
```
ALERT_SLACK_WEBHOOK_URL=
ALERT_EMAIL_TO=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
```

**체크리스트 — P4-3**
- [ ] Slack 웹훅 발송 동작 확인
- [ ] SMTP 이메일 발송 동작 확인
- [ ] 동일 소스 경보 중복 방지 (쿨다운 1시간)
- [ ] `GET /admin/alerts` 최근 경보 이력 반환

---

## Session 3 — P5-1: React Native (Expo) 기반 구축

**목표**: Expo 신규 프로젝트, 탭 네비게이션, 백엔드 API 연동 카드 피드

**생성 파일**
```
mobile/
├── app.json                     # Expo 설정 (bundleId, icon, splash)
├── package.json                 # expo, expo-router, nativewind, zustand, axios
├── app/
│   ├── _layout.tsx              # Root layout (Stack + Tab 네비게이션)
│   ├── (tabs)/
│   │   ├── _layout.tsx          # 탭 레이아웃 (피드·북마크·설정)
│   │   ├── index.tsx            # 피드 탭 (카드 FlatList, 기본 렌더링)
│   │   ├── bookmarks.tsx        # 북마크 탭
│   │   └── settings.tsx         # 설정 탭 (로그인 상태 표시)
│   └── cards/[id].tsx           # 카드 상세 화면
├── lib/
│   ├── api.ts                   # axios 기반 백엔드 클라이언트
│   └── types.ts                 # CardNews, CardTechnique, FeedResponse 타입
└── stores/
    └── auth.ts                  # Zustand 인증 상태 (token, user, setUser)
```

**체크리스트**
- [ ] `npx expo start` iOS/Android 시뮬레이터 기동 확인
- [ ] 탭 3개 전환 확인 (피드·북마크·설정)
- [ ] `GET /cards` 응답 → 카드 타이틀 목록 FlatList 렌더링 확인
- [ ] NativeWind 스타일링 동작 확인
- [ ] `EXPO_PUBLIC_API_URL` env 로딩 확인
- [ ] `mobile/` 디렉토리 docker-compose와 독립 실행 확인

---

## Session 4 — P5-2: 모바일 카드 UI + 스와이프 제스처

**목표**: NEWS/TECHNIQUE 카드 컴포넌트 + react-native-gesture-handler 스와이프

**생성 파일**
```
mobile/components/
├── cards/
│   ├── MobileNewsCard.tsx           # 미리보기 (제목, 요약 2줄, 태그, 날짜)
│   ├── MobileNewsCardExpanded.tsx   # What/Why/Impact 전체 + 원본 링크
│   ├── MobileTechniqueCard.tsx      # 미리보기 (기법명, 문제 2줄)
│   ├── MobileTechniqueCardExpanded.tsx  # 4단 구조 스크롤
│   ├── CardBadges.tsx               # 타입·카테고리·난이도 뱃지
│   └── SwipeableCard.tsx            # 스와이프 래퍼 (좌=북마크, 우=스킵)
└── ui/
    └── CodeBlock.tsx                # react-native-syntax-highlighter
```

**스와이프 동작**
- 왼쪽 스와이프 → 북마크 저장 (파란 오버레이 + 🔖 표시)
- 오른쪽 스와이프 → 스킵/다음 카드 (회색 오버레이 + → 표시)
- 탭 → 카드 상세 펼치기 토글 (Reanimated 애니메이션)

**체크리스트**
- [ ] NEWS 카드 탭 → 상세 펼치기 애니메이션 확인
- [ ] TECHNIQUE 카드 4단 구조 스크롤 렌더링 확인
- [ ] 스와이프 북마크 → API 저장 + 낙관적 UI 업데이트
- [ ] 코드 블록 언어별 하이라이팅 확인
- [ ] 비로그인 스와이프 북마크 → 로그인 유도 모달

---

## Session 5 — P5-3: 푸시 알림 + 카카오 로그인

**목표**: Expo Push Notification 연동 + 카카오 OAuth (모바일·백엔드 동시)

### 백엔드 작업

**생성/수정 파일**
```
backend/app/
├── routers/auth.py          # /auth/kakao, /auth/kakao/callback 추가
├── services/auth.py         # 카카오 OAuth 처리 추가
└── routers/push.py          # POST /push/register (디바이스 토큰 저장)

backend/alembic/versions/
└── 0002_add_user_devices.py # user_devices 테이블 마이그레이션
```

### 모바일 작업

**생성/수정 파일**
```
mobile/
├── lib/notifications.ts         # Expo Notifications 권한 요청 + 토큰 등록
├── app/(tabs)/settings.tsx      # 알림 ON/OFF 토글 UI + 카카오 로그인 버튼
└── components/auth/
    └── SocialLoginButtons.tsx   # Google·GitHub·카카오 버튼
```

**푸시 알림 트리거**
- 새 배치 완료 후 관심 카테고리 신규 카드 N건 → Expo Push API 발송
- 알림 OFF 사용자 발송 제외

**추가 환경변수**
```
KAKAO_CLIENT_ID=
KAKAO_CLIENT_SECRET=
EXPO_ACCESS_TOKEN=
```

**체크리스트**
- [ ] 카카오 로그인 → JWT 발급 e2e 확인
- [ ] `user_devices` 테이블 마이그레이션 완료
- [ ] 디바이스 토큰 DB 저장 + 중복 등록 방지
- [ ] 배치 완료 후 Expo Push API 발송 확인
- [ ] 알림 OFF 사용자 제외 확인
- [ ] 앱 포그라운드/백그라운드 알림 수신 확인

---

<!-- S5→S6: mobile/package.json에 expo-notifications@~0.29.14, expo-web-browser@~14.0.2 추가됨, npm install 필요 -->

## Session 6 — P5-4 + P5-5: 파이프라인 소스 확장

### P5-4: 소스 그룹 B-2 / B-3 / C-2

**생성 파일**
```
pipeline/adapters/
└── github_trending.py       # GitHub Trending 페이지 스크래핑 (requests + BS4)

pipeline/sources/
├── group_b2.py              # B-2: GitHub Trending AI/ML 일별 리포 목록
├── group_b3.py              # B-3: awesome-llm 등 5개 awesome-* README 파싱
└── group_c2.py              # C-2: 개인 블로그 RSS (Simon Willison 등 8개)
```

---

### P5-5: 소스 그룹 D-2 (IMAP 이메일)

**생성 파일**
```
pipeline/adapters/
└── imap.py                  # IMAP 수신함 → 최근 6시간 이메일 파싱

pipeline/sources/
└── group_d2.py              # D-2: The Batch, Import AI, TLDR AI 등 뉴스레터
```

**추가 환경변수**
```
IMAP_HOST=
IMAP_USER=
IMAP_PASSWORD=
IMAP_MAILBOX=INBOX
```

**공통 체크리스트**
- [ ] GitHub Trending AI 카테고리 일별 리포 수집 확인
- [ ] awesome-llm README 신규 항목 추출 확인
- [ ] Simon Willison 블로그 RSS 수집 확인
- [ ] IMAP 수신함 최근 6시간 이메일 파싱 확인
- [ ] 신규 소스 `source_group` 태깅 올바르게 설정 확인
- [ ] `docs/content-sources.md` 신규 소스 목록 업데이트
- [ ] orchestrate.py에 신규 그룹 태스크 등록 확인

---

## Session 7 — P6-1: 협업 필터링 추천

**목표**: 사용자-카드 상호작용 매트릭스 기반 CF 추천 (P1-4 규칙 기반 추천 업그레이드)

**생성/수정 파일**
```
backend/app/
├── services/recommendations.py  # CF 로직으로 교체 (기존 규칙 기반 유지 폴백)
└── tasks/build_cf_model.py      # 일 1회 모델 재학습 Celery 태스크

pipeline/tasks/
└── train_cf.py                  # implicit ALS 모델 학습 + Redis 벡터 저장
```

**추천 알고리즘**
```
1. user-card 상호작용 매트릭스 구성
   (like=1.0, bookmark=2.0, view=0.3 가중치)
2. implicit ALS (alternating least squares) 모델 학습
   - factors=64, iterations=20, regularization=0.1
3. 사용자 벡터 → 카드 벡터 코사인 유사도 Top-K
4. 신규 사용자 (cold start) → P1-4 규칙 기반 폴백
5. 학습 모델 Redis에 직렬화 저장, 조회 시 로드
```

**체크리스트**
- [ ] `implicit` 라이브러리 pyproject.toml 추가
- [ ] 일 1회 모델 재학습 Beat 스케줄 등록 확인
- [ ] cold start 사용자 → 규칙 기반 폴백 동작 확인
- [ ] `GET /cards/recommended` 응답이 CF 결과로 교체됨 확인
- [ ] 학습 데이터 부족 시 (좋아요 < 5건) 폴백 확인
- [ ] 모델 학습 시간 측정 + Beat 스케줄과 충돌 없음 확인

---

## Session 8 — P6-2: Elasticsearch 전환 + nori 형태소 분석

**목표**: Meilisearch → Elasticsearch 마이그레이션, 한국어 nori 분석기 적용

**생성/수정 파일**
```
backend/app/
├── services/search.py       # Elasticsearch 클라이언트로 교체
└── tasks/index_card.py      # ES 인덱싱 로직으로 교체

backend/es/
├── mappings/cards.json      # cards 인덱스 매핑 (nori 분석기 포함)
└── setup.py                 # 인덱스 생성 + 기존 카드 전체 재인덱싱 스크립트
```

**ES 인덱스 매핑 핵심**
```json
{
  "settings": {
    "analysis": {
      "analyzer": {
        "korean": {
          "type": "custom",
          "tokenizer": "nori_tokenizer",
          "filter": ["nori_part_of_speech"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title":   { "type": "text", "analyzer": "korean" },
      "summary": { "type": "text", "analyzer": "korean" },
      "tags":    { "type": "keyword" },
      "category":    { "type": "keyword" },
      "card_type":   { "type": "keyword" },
      "difficulty":  { "type": "keyword" },
      "published_at":{ "type": "date" },
      "like_count":  { "type": "integer" }
    }
  }
}
```

**마이그레이션 절차**
1. ES 컨테이너 + nori 플러그인 docker-compose 추가
2. `es/setup.py` 실행 → 인덱스 생성 + 전체 카드 재인덱싱
3. `services/search.py` Meilisearch → ES 클라이언트 교체
4. `tasks/index_card.py` ES 인덱싱으로 교체
5. docker-compose에서 Meilisearch 서비스 제거

**체크리스트**
- [ ] nori 플러그인 설치된 ES 컨테이너 기동 확인
- [ ] `es/setup.py` 실행 후 전체 카드 인덱싱 완료
- [ ] 한국어 형태소 분석 검색 (`RAG` → `RAG 패턴` 연관 결과) 확인
- [ ] 기존 Meilisearch 대비 검색 결과 품질 비교 확인
- [ ] 카드 INSERT 후 ES 자동 인덱싱 확인
- [ ] docker-compose에서 Meilisearch 제거 후 에러 없음 확인
- [ ] `.env.example`에 `ELASTICSEARCH_URL` 추가, `MEILISEARCH_*` 제거
