# API 설계 — AI Pulse

> FastAPI 기준. OpenAPI 스펙은 `/docs` (Swagger UI) 자동 생성.

## Base URL

```
https://api.aipulse.kr/v1
```

## 인증

소셜 로그인(Google / GitHub / Kakao) OAuth 2.0 → JWT 발급.

```
Authorization: Bearer <access_token>
```

게스트는 토큰 없이 조회 가능. 좋아요·북마크·추천은 토큰 필수.

---

## 엔드포인트 목록

### 카드 피드

| Method | Path | 설명 | 인증 |
|---|---|---|---|
| GET | `/cards` | 카드 피드 (무한 스크롤) | 선택 |
| GET | `/cards/{id}` | 카드 상세 | 선택 |
| GET | `/cards/recommended` | 개인화 추천 피드 | 필수 |

**GET /cards 쿼리 파라미터**

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `category` | enum | all | `CODING` \| `DESIGN` \| `GENERAL` \| `all` |
| `card_type` | enum | all | `NEWS` \| `TECHNIQUE` \| `all` |
| `tags` | string[] | - | 태그 슬러그 배열 (AND 조건) |
| `difficulty` | enum | - | `BEGINNER` \| `INTERMEDIATE` \| `ADVANCED` |
| `cursor` | string | - | 페이지네이션 커서 (published_at 기준) |
| `limit` | int | 20 | 최대 50 |

**응답 예시 (NEWS 카드)**

```json
{
  "items": [
    {
      "id": "crd_01HZ...",
      "card_type": "NEWS",
      "category": "GENERAL",
      "difficulty": "BEGINNER",
      "title": "Claude 4.7 출시 — 추론 속도 2배 향상",
      "summary": "Anthropic이 Claude 4.7을 출시했다...",
      "key_points": ["추론 속도 2배", "컨텍스트 200K 토큰", "API 가격 동결"],
      "source_url": "https://anthropic.com/news/...",
      "source_name": "Anthropic",
      "source_group": "NEWS_RSS",
      "tags": ["#LLM", "#ModelRelease"],
      "thumbnail_url": "https://cdn.aipulse.kr/...",
      "like_count": 42,
      "bookmark_count": 15,
      "published_at": "2026-05-26T06:00:00+09:00"
    }
  ],
  "next_cursor": "2026-05-26T00:00:00+09:00",
  "has_more": true
}
```

**응답 예시 (TECHNIQUE 카드)**

```json
{
  "id": "crd_02AB...",
  "card_type": "TECHNIQUE",
  "category": "CODING",
  "difficulty": "INTERMEDIATE",
  "title": "Multi-Agent Harness 패턴",
  "problem": "단일 LLM 호출로 복잡한 워크플로를 처리하면 컨텍스트가 폭발한다...",
  "idea": "에이전트를 역할별로 분리하고 오케스트레이터가 조율하는 하네스 구조를 사용한다...",
  "code_snippet": "# 핵심 코드 스니펫\norchestrator = Orchestrator(agents=[...])",
  "caveats": ["API 비용이 단일 호출 대비 3~5배", "디버깅 복잡도 증가", "상태 동기화 주의"],
  "prerequisites": "LangGraph 기본 사용법",
  "source_url": "https://blog.langchain.dev/...",
  "source_name": "LangChain",
  "source_group": "ENG_BLOG",
  "tags": ["#Agents", "#LangGraph", "#AgenticAI"]
}
```

---

### 좋아요 / 북마크

| Method | Path | 설명 | 인증 |
|---|---|---|---|
| POST | `/cards/{id}/like` | 좋아요 추가 | 필수 |
| DELETE | `/cards/{id}/like` | 좋아요 취소 | 필수 |
| POST | `/cards/{id}/bookmark` | 북마크 추가 | 필수 |
| DELETE | `/cards/{id}/bookmark` | 북마크 취소 | 필수 |
| GET | `/me/bookmarks` | 내 북마크 목록 | 필수 |

---

### 검색

| Method | Path | 설명 | 인증 |
|---|---|---|---|
| GET | `/search` | 카드 검색 | 선택 |

**GET /search 쿼리 파라미터**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `q` | string | 검색어 (한국어 지원) |
| `category` | enum | 카테고리 필터 |
| `card_type` | enum | 타입 필터 |
| `limit` | int | 최대 20 |

---

### 인증

| Method | Path | 설명 |
|---|---|---|
| GET | `/auth/{provider}` | OAuth 리다이렉트 (`google` \| `github` \| `kakao`) |
| GET | `/auth/{provider}/callback` | OAuth 콜백 → JWT 발급 |
| POST | `/auth/refresh` | 토큰 갱신 |
| DELETE | `/auth/logout` | 로그아웃 |

---

### 사용자

| Method | Path | 설명 | 인증 |
|---|---|---|---|
| GET | `/me` | 내 프로필 | 필수 |
| GET | `/me/bookmarks` | 북마크 목록 (카테고리·타입 필터) | 필수 |

---

### 관리자 (Admin)

| Method | Path | 설명 |
|---|---|---|
| GET | `/admin/batches` | 배치 실행 이력 |
| GET | `/admin/batches/{batch_id}` | 배치 상세 (소스별 수집량, 비용) |
| GET | `/admin/sources/health` | 소스 헬스체크 현황 |
| PATCH | `/admin/sources/{source_id}` | 소스 활성화/비활성화 |
| GET | `/admin/translation-queue` | 수동 검토 큐 |
| GET | `/admin/metrics` | DAU/MAU, API 비용, 카드 타입 분포 |

---

## 에러 응답 형식

```json
{
  "error": {
    "code": "CARD_NOT_FOUND",
    "message": "요청한 카드를 찾을 수 없습니다.",
    "status": 404
  }
}
```

## 페이지네이션

커서 기반 페이지네이션 사용 (`published_at` 기준 역순).

```
GET /cards?cursor=2026-05-26T00:00:00%2B09:00&limit=20
```

## OG 이미지 생성

```
GET /cards/{id}/og-image
→ PNG (1200×630) 자동 생성, CDN 캐싱
```
