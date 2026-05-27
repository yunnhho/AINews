# AI Pulse — 미완료 작업 목록

> 마지막 확인: 2026-05-27 (Session 8 완료 후)

---

## 1. P2-3 — GitHub 403 응답 시 source_health 기록 누락

**분류**: 버그  
**파일**: `pipeline/pipeline/adapters/github.py:42-44`

```python
if resp.status_code == 403:
    # Rate limit — 현재 빈 목록만 반환, source_health 기록 없음
    return []
```

**해야 할 것**: `return []` 앞에 `record_failure()` 호출 추가

```python
if resp.status_code == 403:
    health_svc.run_sync(
        health_svc.record_failure(self.source_name, "GITHUB", "403 rate limit")
    )
    return []
```

**근거**: `pipeline/pipeline/sources/group_b.py`의 404 처리와 동일하게, 403도 연속 실패 카운트에 포함해야 함. 스펙: `403 응답 → source_health 기록 + 다음 배치 연기`

---

## 2. P4-1 — Admin 번역 검토 approve/reject UI 없음

**분류**: 기능 누락  
**파일**: `frontend/app/admin/translation/page.tsx`

번역 이력 조회·펼쳐보기는 구현됐으나, 통과(approve)/삭제(reject) 버튼이 없음.  
API 메서드(`adminApi.reviewTranslation`)는 `frontend/lib/admin-api.ts`에 존재하나 미사용.

**해야 할 것**: 펼쳐진 아이템 하단에 버튼 추가

```tsx
{!item.passed && (
  <div className="flex gap-2 mt-3">
    <button onClick={() => handleReview(item.id, 'approve')}>✅ 통과</button>
    <button onClick={() => handleReview(item.id, 'reject')}>🗑️ 삭제</button>
  </div>
)}
```

**근거**: 스펙 `수동 검토 큐: 카드 내용 확인 + 통과/삭제 액션`

---

## 3. P3-6 — 카카오 공유 버튼 미구현

**분류**: 기능 누락  
**파일**: `frontend/components/cards/CardActions.tsx:52-59`

현재 `navigator.share` (Web Share API)로만 구현됨. 카카오 SDK 직접 연동 버튼 없음.

**해야 할 것**:
1. 카카오 JavaScript SDK `@types/kakao.maps.d.ts` 또는 직접 스크립트 로드
2. `KAKAO_JS_KEY` env 추가 (`.env.example`)
3. `CardActions.tsx`에 카카오 공유 버튼 추가

**근거**: 스펙 `카카오톡 공유 버튼 동작 확인`

---

## 4. P3-6 — PWA 아이콘 파일 없음

**분류**: 에셋 누락  
**파일**: `frontend/public/` (파일 없음)

`frontend/public/manifest.json`이 아래를 참조하지만 실제 파일 없음:
- `/icon-192.png` (192×192)
- `/icon-512.png` (512×512)

**해야 할 것**: 아이콘 이미지 생성 후 `frontend/public/`에 추가

---

## 5. `.env.example` — `NEXT_PUBLIC_SITE_URL` 누락

**분류**: 문서 누락  
**파일**: `.env.example`

다음 파일에서 `NEXT_PUBLIC_SITE_URL` 사용 중이나 `.env.example`에 키가 없음:
- `frontend/app/cards/[id]/page.tsx`
- `frontend/app/sitemap.ts`
- `frontend/app/robots.ts`

**해야 할 것**: `.env.example`에 아래 추가

```
NEXT_PUBLIC_SITE_URL=https://aipulse.kr
```
