# 컨텍스트 가이드

## 새 컨텍스트 시작 시 읽을 파일

| 작업 그룹 | 필수 읽기 |
|---|---|
| 모든 작업 공통 | `CLAUDE.md` + `docs/phases.md` |
| 백엔드 (P1) | + `docs/erd.md` + `docs/api-design.md` |
| 파이프라인 (P2) | + `docs/erd.md` + `docs/pipeline.md` + `docs/content-sources.md` |
| 웹 프론트 (P3) | + `docs/api-design.md` |
| 관리자 (P4) | + `docs/api-design.md` + `docs/pipeline.md` |

## 컨텍스트 전환 타이밍

각 Phase의 **체크리스트가 전부 통과**되면 새 컨텍스트로 전환.

```
P0-1 완료 → 새 컨텍스트 → P0-2
P0-2 완료 → 새 컨텍스트 → P1-1
P1-1 완료 → 새 컨텍스트 → P1-2 (또는 P2-1 병렬 시작)
P1-2 완료 → 새 컨텍스트 → P1-3
P1-3 완료 → 새 컨텍스트 → P1-4 // P1-5 // P2-2 // P2-3 // P2-4 (병렬 가능)
P2-2~4 완료 → 새 컨텍스트 → P2-5
P2-5 완료 → 새 컨텍스트 → P2-6
P2-6 완료 → 새 컨텍스트 → P2-7
P3-2 완료 → 새 컨텍스트 → P3-3 // P3-4 (병렬 가능)
```

## 현재 진행 상황 기록

> 이 섹션을 직접 업데이트하며 사용

- [x] P0-1 — 레포 구조 + Docker Compose
- [x] P0-2 — DB 스키마 + Alembic
- [x] P1-1 — FastAPI 골격
- [x] P1-2 — 인증 (OAuth + JWT)
- [x] P1-3 — 카드 피드 API
- [x] P1-4 — 좋아요·북마크 + 추천
- [x] P1-5 — 검색 API
- [x] P2-1 — Celery·Beat + 배치 로깅
- [x] P2-2 — 소스 어댑터 그룹 A
- [x] P2-3 — 소스 어댑터 그룹 B-1
- [x] P2-4 — 소스 어댑터 그룹 C-1·D-1
- [ ] P2-5 — 중복 필터링
- [ ] P2-6 — Claude API NEWS
- [ ] P2-7 — Claude API TECHNIQUE + 번역 검증
- [ ] P3-1 — Next.js 기반 + 레이아웃
- [ ] P3-2 — 카드 피드 페이지
- [ ] P3-3 — NEWS 카드 컴포넌트
- [ ] P3-4 — TECHNIQUE 카드 컴포넌트
- [ ] P3-5 — 인증 UI + 인터랙션
- [ ] P3-6 — SEO + OG 이미지 + PWA
- [ ] P4-1 — 관리 대시보드
