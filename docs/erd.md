# ERD — AI Pulse 데이터 모델

> 기준 버전: PRD v3.0

## 테이블 관계도

```
┌──────────────┐       ┌──────────────────────┐       ┌──────────────┐
│    users     │       │        cards         │       │     tags     │
├──────────────┤       ├──────────────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)              │       │ id (PK)      │
│ provider     │       │ card_type (enum)     │       │ name         │
│ provider_id  │       │ title                │       │ slug         │
│ nickname     │       │ summary              │       │ category     │
│ avatar_url   │       │ key_points[] ¹       │       └──────┬───────┘
│ created_at   │       │ problem ²            │              │
│ updated_at   │       │ idea ²               │       ┌──────┴───────────┐
└──────┬───────┘       │ code_snippet ²       │       │   card_tags      │
       │               │ caveats[] ²          │       ├──────────────────┤
       │               │ prerequisites ²      │       │ card_id (FK)     │
       │               │ source_url           │◄──────│ tag_id  (FK)     │
       │               │ source_name          │       └──────────────────┘
       │               │ source_group (enum)  │
       │               │ original_lang        │
       │               │ category (enum)      │
       │               │ difficulty (enum)    │
       │               │ thumbnail_url        │
       │               │ like_count           │
       │               │ bookmark_count       │
       │               │ batch_id             │
       │               │ published_at         │
       │               │ created_at           │
       │               └────────┬─────────────┘
       │                        │
       ├────────────────────────┤
       │                        │
       ▼                        ▼
┌──────────────────┐    ┌──────────────────┐
│    user_likes    │    │  user_bookmarks  │
├──────────────────┤    ├──────────────────┤
│ user_id (FK)     │    │ user_id (FK)     │
│ card_id (FK)     │    │ card_id (FK)     │
│ created_at       │    │ created_at       │
│ UNIQUE(user_id,  │    │ UNIQUE(user_id,  │
│  card_id)        │    │  card_id)        │
└──────────────────┘    └──────────────────┘

┌──────────────────────────┐    ┌──────────────────────────┐
│   translation_logs       │    │     batch_logs           │
├──────────────────────────┤    ├──────────────────────────┤
│ id (PK)                  │    │ id (PK)                  │
│ card_id (FK)             │    │ batch_id (unique)        │
│ original_text            │    │ scheduled_at             │
│ translated_text          │    │ started_at               │
│ back_translated_text     │    │ completed_at             │
│ similarity_score (float) │    │ status (enum)            │
│ passed (boolean)         │    │ collected_by_group (jsonb│
│ retry_count              │    │   {A:N, B:N, C:N, D:N}  │
│ created_at               │    │ deduplicated_count       │
└──────────────────────────┘    │ published_by_type (jsonb)│
                                │   {NEWS:N, TECHNIQUE:N}  │
┌──────────────────────────┐    │ failed_count             │
│   source_health          │    │ api_tokens_used          │
├──────────────────────────┤    │ api_cost_usd (decimal)   │
│ source_id (PK)           │    │ error_log (text, null)   │
│ source_name              │    └──────────────────────────┘
│ source_group (enum)      │
│ last_success_at          │
│ consecutive_failures     │
│ last_error_log           │
│ enabled (boolean)        │
└──────────────────────────┘

¹ NEWS 카드 전용   ² TECHNIQUE 카드 전용
```

## Enum 정의

| Enum | 값 |
|---|---|
| `card_type` | `NEWS` \| `TECHNIQUE` |
| `category` | `CODING` \| `DESIGN` \| `GENERAL` |
| `difficulty` | `BEGINNER` \| `INTERMEDIATE` \| `ADVANCED` |
| `original_lang` | `KO` \| `EN` \| `JA` \| `ZH` |
| `batch_status` | `SCHEDULED` \| `RUNNING` \| `COMPLETED` \| `PARTIAL_FAILURE` \| `FAILED` |
| `source_group` | `NEWS_RSS` \| `GITHUB` \| `ENG_BLOG` \| `NEWSLETTER` |

## 카드 타입별 필드 사용 여부

| 필드 | NEWS | TECHNIQUE | 비고 |
|---|---|---|---|
| `summary` | ✅ | ✅ | What/Why/Impact 요약 |
| `key_points[]` | ✅ | ❌ | 2~3개 불릿 |
| `problem` | ❌ | ✅ 필수 | 해결하는 문제 |
| `idea` | ❌ | ✅ 필수 | 핵심 아이디어 |
| `code_snippet` | ❌ | ⭕ 선택 | 원본 추출만, 최대 15줄 |
| `caveats[]` | ❌ | ✅ 필수 | 1~3개 주의점 |
| `prerequisites` | ❌ | ⭕ 선택 | 선행 지식 |

## DDL 핵심 제약 조건

```sql
-- 카드 타입 무결성 보장
ALTER TABLE cards ADD CONSTRAINT card_type_fields CHECK (
  (card_type = 'NEWS' AND key_points IS NOT NULL AND problem IS NULL)
  OR
  (card_type = 'TECHNIQUE' AND problem IS NOT NULL AND idea IS NOT NULL)
);

-- 좋아요 중복 방지
ALTER TABLE user_likes ADD CONSTRAINT uq_user_likes UNIQUE (user_id, card_id);

-- 북마크 중복 방지
ALTER TABLE user_bookmarks ADD CONSTRAINT uq_user_bookmarks UNIQUE (user_id, card_id);

-- batch_id 유일성
ALTER TABLE batch_logs ADD CONSTRAINT uq_batch_id UNIQUE (batch_id);
```

## 인덱스 전략

```sql
-- 피드 조회 (카테고리·타입·발행일 복합)
CREATE INDEX idx_cards_feed ON cards (category, card_type, published_at DESC);

-- 태그 검색
CREATE INDEX idx_card_tags_tag ON card_tags (tag_id);

-- 사용자 북마크 조회
CREATE INDEX idx_bookmarks_user ON user_bookmarks (user_id, created_at DESC);

-- 배치 로그 조회
CREATE INDEX idx_batch_logs_scheduled ON batch_logs (scheduled_at DESC);

-- 소스 헬스체크
CREATE INDEX idx_source_health_group ON source_health (source_group, enabled);
```
