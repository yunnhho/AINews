# AI Pulse — CLAUDE.md (대규칙)

AI/LLM 뉴스 카드 플랫폼. 세부 규칙은 각 하위 모듈 `CLAUDE.md` 참조.

## 기술 스택
- 백엔드: FastAPI(Python 3.12) + Celery + PostgreSQL + Redis
- 프론트: Next.js 15(App Router, SSR) + React Native(Expo)
- AI: Claude API(요약·분류·번역) + sentence-transformers(검증)

## 세션 인수인계 규칙

- `docs/sessions.md`의 각 세션 작업 완료 후, 다음 세션에 꼭 전달할 내용이 있으면 **다음 세션 문서의 가장 위에 3-40자 이내로 추가**한다
- 전달 내용 없으면 추가하지 않는다

## 핵심 규칙

- 카드 타입은 반드시 `NEWS` / `TECHNIQUE` 두 가지로 구분한다
- 배치 수집은 Celery Beat, KST 00/06/12/18시 4회 실행한다
- Claude API 호출은 타입별 프롬프트를 분리하여 사용한다
- 번역 검증은 역번역 후 코사인 유사도 0.85 이상만 통과시킨다
- 코드 스니펫은 LLM이 생성하지 않고 원본에서 추출만 한다
- DB는 단일 `cards` 테이블 + 타입별 nullable 컬럼 구조를 유지한다
- 소스 그룹 A(뉴스RSS)·B(GitHub)·C(엔지블로그)·D(뉴스레터) 순으로 도입한다
- 원본 전문 저장 금지, 반드시 원본 URL을 카드에 노출한다

## 문서 위치

| 문서 | 경로 |
|---|---|
| ERD (데이터 모델) | `docs/erd.md` |
| 시스템 아키텍처 | `docs/architecture.md` |
| 배치 파이프라인 명세 | `docs/pipeline.md` |
| 콘텐츠 소스 목록 | `docs/content-sources.md` |
| API 설계 | `docs/api-design.md` |
| 문제·해결·결과 (예상·실제 문제 + 설계 의사결정) | `docs/problem-solution-result.md` |
| 배포 전 보안 점검 (취약점·수정·구현 요약) | `docs/security-audit.md` |
| 보안 수정 테스트 시나리오 | `docs/security-test-scenarios.md` |

## 세부 CLAUDE.md 위치 (예정)

```
backend/CLAUDE.md       — FastAPI 라우터·서비스 레이어 규칙
pipeline/CLAUDE.md      — Celery 태스크·어댑터 패턴 규칙
frontend/CLAUDE.md      — Next.js 컴포넌트·라우팅 규칙
mobile/CLAUDE.md        — React Native(Expo) 규칙
```
