# AI Pulse — 유지보수 로그 (Maintenance Log)

> 스프린트(`sessions.md`) 이후의 버그 수정·기능 추가·운영 변경을 상세히 기록한다.
> 각 항목은 **배경/문제 → 변경 파일 → 구현 상세 → 검증**으로 정리한다.
> 요약 인덱스는 메모리 `project_status.md`, 기술 의사결정은 `PROBLEM_SOLUTION_RESULT.md` 참조.

---

## 2026-06-09 — 만료 토큰 버그 수정 + 폰트 Pretendard 전환

### 1. 만료 토큰으로 전 기능이 "안 됨" (실버그)

**문제**
- 저장된 JWT는 60분 만료(`JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60`)인데, zustand `persist`
  스토어가 만료된 `token`+`user`를 그대로 유지했다.
- 결과: 헤더는 로그인 상태(`yunnhho`)로 보이지만 좋아요·북마크·추천·북마크 페이지의
  모든 인증 요청이 **401로 조용히 롤백** → 사용자에겐 "기능이 전부 안 됨"으로 보임.
- 근본 원인: 만료 토큰을 감지·정리하는 로직이 프론트 어디에도 없었다.

**변경 파일**
- `frontend/stores/auth.ts`
- `frontend/lib/api.ts`
- `frontend/components/cards/CardActions.tsx`

**구현 상세**
1. `stores/auth.ts` — `isTokenExpired(token)` 추가(JWT `exp` 디코드, 형식 깨지면 만료로 간주).
   `persist`의 `onRehydrateStorage`에서 복원 시 만료면 `token/user`를 즉시 비운다.
2. `lib/api.ts` — `setUnauthorizedHandler(fn)` 전역 핸들러 등록 API 추가.
   `request()`가 **토큰을 보낸 요청에서 401**을 받으면 핸들러를 호출한다(세션 중 만료 복구).
3. `stores/auth.ts` — 모듈 로드 시(클라이언트) `setUnauthorizedHandler(() => logout())` 등록.
4. `CardActions.tsx` — 좋아요/북마크 `catch`에서 `ApiError.status === 401`이면
   조용한 롤백 대신 `AuthModal`을 띄워 재로그인을 유도.

**검증 (Playwright E2E, 콘솔 에러 0)**
- 만료 토큰으로 새로고침 → 헤더가 올바르게 "로그인" 버튼 표시(자동 정리됨).
- 신선한 JWT 주입 후 좋아요 ♥1 / 북마크 ■1 동작 + 새로고침 후에도 서버 상태 유지.
- 검색("프롬프트 인젝션" 1건)·추천(3건)·북마크 페이지·카드 상세(TECHNIQUE 4단+코드블록) 정상.
- `tsc --noEmit` 통과.

### 2. 폰트 → Pretendard 전환 (가독성/친숙도)

**배경**
- 직전 에디토리얼 리디자인은 명조체 헤드라인(Nanum Myeongjo)+IBM Plex Sans KR 본문이었으나,
  한국 IT/AI 독자에게는 **Pretendard**가 가장 익숙하고 작은 크기에서도 가독성이 높다.

**변경 파일**
- `frontend/app/layout.tsx` — jsDelivr Pretendard Variable dynamic-subset CDN `<link>` 추가,
  기존 Nanum Myeongjo/IBM Plex Sans KR 제거(IBM Plex Mono는 라벨용으로 유지).
- `frontend/app/globals.css` — `--font-sans`/`--font-serif`를 Pretendard로 통일.
- (tailwind.config.ts는 CSS 변수 참조라 자동 반영)

**결과**
- 본문·헤드라인 모두 Pretendard로 통일. 에디토리얼 팔레트(paper/ink/vermillion),
  레이아웃, 모노 라벨(NEWS/TECHNIQUE/태그)은 그대로 유지해 디자인 정체성 보존.

---

## 2026-06-09 — GitHub 수집 기준 확장 (B-2 topic 추가 + B-4 신설)

### 3. B-2에 `claude-md` topic 추가

**배경**
- GitHub 수집(그룹 B)은 B-1(라이브러리 Releases), B-2(topic 트렌딩 Search),
  B-3(awesome 리스트 README diff)로 구성. CLAUDE.md 관련 트렌딩 리포를 포함하고 싶었다.
- GitHub API로 후보 topic 실측: `claude-md`(별≥30 → 12개, 정확) vs
  `claude`/`claude-code`(2,300~2,966개, 과도하게 넓어 노이즈). → `claude-md` 채택.

**변경 파일**
- `pipeline/pipeline/sources/group_b2.py` — `_B2_TOPICS`에 `("claude-md", 30)` 추가.
- `docs/content-sources.md` — B-2 표에 `topic:claude-md` 행 추가.

**수집 기준 정리 (그룹 B 전체)**

| 그룹 | 대상 | 기준 | 구현 |
|---|---|---|---|
| B-1 | 라이브러리 9종 Releases | 최근 6.5h + 본문 ≥300자(단순 버전업 제외) | `group_b.py` |
| B-2 | topic 트렌딩 (llm·rag·mcp·ai-coding·claude-md 등) | `topic:X stars:>=N pushed:>날짜`, 일1회 KST 00시 | `group_b2.py` |
| B-3 | awesome-* 4종 README | README.md 커밋 diff의 신규 링크 항목 | `group_b3.py` |
| B-4 | 큐레이션 CLAUDE.md (신설) | 특정 파일 경로 직접 fetch, DB 미존재 시만 | `group_b4.py` |

### 4. B-4 — 큐레이션 CLAUDE.md 직접 수집 소스 (신설)

**배경/문제**
- B-2의 topic 검색은 **self-tagging된 리포만** 잡는다. 예시로 받은
  `multica-ai/andrej-karpathy-skills`(⭐171,871, description이 "A single CLAUDE.md file
  to improve Claude Code behavior...")는 `topics: []`라 매칭되지 않고, `pushed: 2026-01-20`
  이라 "최근 6.5h" 윈도우에도 안 걸려 **완전히 누락**된다.
- 즉 topic·푸시시점과 무관하게 핵심 파일을 확실히 수집할 별도 메커니즘이 필요.

**변경 파일**
- `pipeline/pipeline/sources/group_b4.py` (신규)
- `pipeline/pipeline/tasks/orchestrate.py` — import / `collect_group_b4()` / `collected_by_group["B4"]`
  / `raw_items`에 `group_b4` 합산.
- `pipeline/scripts/test_run.py` — `collect_group_b4()`를 수집 맨 앞에 추가
  (B-4 항목을 맨 앞에 둬 `limit=1` 실행 시 큐레이션 파일만 우선 처리).
- `docs/content-sources.md` — B-4 섹션 추가.

**구현 상세**
- `_B4_FILES = [{repo, path, branch, name}]` 큐레이션 목록. raw API
  (`GET /repos/{repo}/contents/{path}`, `Accept: application/vnd.github.raw`)로 원문 fetch.
- `source_url = https://github.com/{repo}/blob/{branch}/{path}` (blob URL).
- `published_at` = 해당 파일 경로의 최신 커밋 시각(commits API).
- 본문 200자 미만 스텁은 스킵, GITHUB 그룹 → **TECHNIQUE 카드**로 처리.
- **재과금 방지**: B-4는 최근 윈도우를 쓰지 않으므로(오래된 파일도 첫 수집 대상),
  AI 파이프라인의 DB 중복 체크(발행 단계, AI 처리 *이후*)만으로는 매 배치 AI 비용이 든다.
  따라서 **수집 단계에서 `Card.source_url` DB 존재 여부를 선체크**(NullPool 비동기 세션 +
  `run_sync`)해 이미 카드화된 파일은 네트워크·AI 비용 0으로 스킵.

**큐레이션 추가 방법**
- 좋은 CLAUDE.md를 발견하면 `group_b4.py`의 `_B4_FILES`에
  `{"repo": "...", "path": "...", "branch": "main", "name": "..."}` 항목을 추가.

**검증 (worker 컨테이너)**
- `collect_group_b4()` → andrej-karpathy CLAUDE.md 2345자 수집, blob URL·커밋일 정상.
- `_source_url_exists` 양방향: 신규 URL=False(수집), 기존 카드 URL=True(스킵).
- `orchestrate` import OK, `py_compile` OK. worker 이미지 재빌드+재기동 반영 확인.

### 5. 예시 CLAUDE.md → 실제 카드 발행 (card 8)

**절차**
- `docker compose run --rm -v .../test_run.py:/app/scripts/test_run.py worker python -m scripts.test_run 1`
  → B-4 항목(andrej-karpathy CLAUDE.md) 1건만 AI 처리.
- 역번역 유사도 **0.701** (임계 0.85 미만 — CLAUDE.md는 산문이 아닌 규칙 나열이라 코사인 낮음)
  → 규정대로 **비공개 초안(검토 큐)** 저장.
- admin 승인 흐름 `handle_translation_review(log_id=7, "approve")` 실행
  → `is_published=True` + ES 색인 → 공개 발행.

**결과**
- **card 8 "Claude.md: LLM 코딩 실수 방지 가이드라인"** (TECHNIQUE, 난이도 입문,
  태그: llm coding / code quality / behavioral guidelines).
  Problem/Idea/Code/Caveats 4단 + 선행지식 + 원문 링크 정상 렌더, 피드 노출 확인.
- 첫 테스트 실행에서 잘못 생성된 무관한 RSS 초안(card 7 Sandstone) 삭제.
  기존 초안 card 2·5는 이전 세션 것이라 유지.
- 비용: 약 $0.0037.

---

## 2026-06-09 — 기본 해킹 방어 및 보안 하드닝

### 6. 보안 미들웨어 + 운영 가드

**현황 점검 결과**
- ✓ `.env`는 git 미추적, `.env` 시크릿은 실값 33자(`change-me` 아님), CORS는 localhost로 제한.
- ✗ HTTP 보안 헤더 없음, 레이트리밋 없음, TrustedHost 없음, 코드 시크릿 기본값 `change-me`.

**변경 파일**
- `backend/app/middleware.py` (신규) — `SecurityHeadersMiddleware`, `RateLimitMiddleware`.
- `backend/app/main.py` — 미들웨어 등록 + 운영 가드(시크릿/docs/TrustedHost).
- `backend/app/config.py` — `ALLOWED_HOSTS`, `RATELIMIT_PER_MINUTE` + `allowed_hosts_list`.
- `frontend/next.config.ts` — `headers()`로 보안 헤더 + CSP.
- `.env.example` — `ALLOWED_HOSTS`, `RATELIMIT_PER_MINUTE` 문서화.

**구현 상세**
- **SecurityHeadersMiddleware** (모든 API 응답):
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy: geolocation=(), microphone=(), camera=()`,
  `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`,
  `Strict-Transport-Security`(운영 전용).
- **RateLimitMiddleware**: Redis 고정 윈도우, IP당 `RATELIMIT_PER_MINUTE`(기본 300)/분.
  `X-Forwarded-For` 첫 IP 우선(프록시 뒤 운영). `/health`·`/docs`·`/redoc`·`/openapi.json` 면제.
  초과 시 429 + `Retry-After`. **Redis 장애 시 통과(fail-open)** — 가용성 우선.
- **main.py 운영 가드** (`APP_ENV=production`일 때만):
  시크릿(`SECRET_KEY`/`JWT_SECRET`)이 `change-me`/빈값이면 부팅 차단(RuntimeError);
  `/docs`·`/redoc`·`/openapi.json` 비활성(정보 노출 최소화);
  `TrustedHostMiddleware`로 Host 헤더 검증(`ALLOWED_HOSTS`). 개발 환경은 전부 완화.
- **프론트 CSP** (`next.config.ts`, 전 경로): Next 인라인 스타일/스크립트 + Pretendard(jsDelivr)
  + Google Fonts + 카카오 SDK + API(`connect-src`)를 허용. 개발 모드만 HMR용 `unsafe-eval` 허용.
  동일 보안 헤더(X-Frame-Options 등) + HSTS(운영) 부착.

**검증**
- API 재빌드+재기동 후 `/health`·`/v1/cards`에 보안 헤더 부착, 정상 200 확인.
- 레이트리밋: 단일 IP로 320요청 → 298×200 + 22×429 (300/분 초과분 차단) 확인.
- 프론트 dev 재시작 후 피드 렌더·카드 확장(CSP 하 API 호출) 콘솔 에러 0,
  보안 헤더+CSP 응답 확인. 개발 `/docs` 200(운영만 비활성).

**미적용(의도)**
- ES/Postgres/Redis의 호스트 포트 노출, ES `xpack.security` 비활성은 로컬 개발 편의용으로 유지
  (운영 배포 시 내부 네트워크 격리 + ES 보안 활성 별도 적용).
- 레이트리밋은 현재 IP 전역 단일 한도(엔드포인트별 차등 아님).

---

## 2026-06-10 — 전수 점검: 실버그 4건 수정 + 월 예산 하드 캡 도입

**실버그 수정**
- **Celery beat 스케줄 시간대 버그** (`pipeline/celery_app.py`): `timezone="Asia/Seoul"` 설정 시
  crontab은 해당 시간대로 해석되는데 UTC 시각(15/21/3/9시)으로 적혀 있어 실제로는
  **KST 15/21/03/09시에 실행**되던 문제. KST 시각(0/6/12/18시) 직접 기재로 수정,
  train_cf도 17시→2시(KST 02:00). 컨테이너 내 `remaining_estimate`로 다음 실행
  시각 = KST 00/06/12/18·02:00 검증 완료.
- **검색 인덱스 매핑 이원화** (`backend/app/services/search.py`): 앱 시작 시 `setup_index()`가
  내장한 구버전 매핑(`.en` 서브필드·`tags.text`·lowercase 없음)으로 인덱스를 생성 →
  ES를 새로 만들면 영어/태그 검색이 조용히 죽는 문제. 단일 출처인
  `es/mappings/cards.json`을 읽도록 통일.
- **프론트 프로덕션 빌드 실패** (`app/(feed)/page.tsx`): 미사용 import(`CardSkeletonList`)가
  ESLint 에러로 `next build` 차단. 제거 후 빌드 통과(16 페이지 생성).
- **SQLAlchemy 관계 중복 기록 경고** (`app/models/card.py`): `Card.card_tags`·`CardTag.card`·
  `CardTag.tag`가 `Card.tags`(secondary)와 같은 FK에 쓰기 경합(SAWarning 4건).
  보조 관계 3개를 `viewonly=True`로 변경. 발행 경로(태그 생성·연결) 실테스트로 회귀 없음 확인.

**업그레이드**
- **월 예산 하드 캡** (`pipeline/tasks/orchestrate.py` + `models/batch_log.py`):
  기존엔 `MONTHLY_BUDGET_USD`가 admin 대시보드 표시용일 뿐 강제 없음(메모리 ⚠️ 항목).
  배치 시작 시 `get_month_cost_usd()`(이달 batch_logs 합계)를 조회, AI 처리 루프가
  `이번 배치 누적 비용 ≥ (예산 − 이달 누적)`에 도달하면 이후 항목 처리 중단.
  수집·디듀프(무료)는 그대로 진행. 비용 조회 실패 시 캡 비활성(fail-open).
  페이크 수집기 테스트: 예산 0 → AI 호출 0회 / 예산 충분 → 전건 처리. 현재 .env 캡 $20.
- **TECHNIQUE summary 공백 방어** (`technique_processor.py`): summary 빈 응답 시 idea[:200] 폴백.
- **orchestrate `collected_by_group` 초기값에 B4 누락** 수정(수집 실패 시 키 자체가 빠지던 문제).
- **ruff 정리**: I001/UP017/UP035/UP007/F401 110건 자동 수정(임포트 정렬·`datetime.UTC`·
  PEP604 등 동작 불변 규칙만). E501·UP042(enum 기반 변경 위험)는 의도적으로 보류.
- docker-compose obsolete `version` 키 제거, `.env.example`에 예산 캡 동작 주석.

**검증**
- API 회귀 16종(피드/필터/카드상세/검색 한·영/auth/me/추천/북마크/admin 6종/좋아요·북마크
  사이클) 전부 통과, 5xx 0건. 비관리자 admin 403, 위조 토큰 게스트 폴백 200 확인.
- worker 컨테이너 재빌드 후 `warnings.simplefilter('error')` 하에서 SAWarning 0건.
- 프론트 `next build` + `next start`로 5개 페이지(피드/검색/북마크/추천/카드상세) SSR 200.
- mobile `tsc --noEmit` 통과. beat는 여전히 의도적으로 미가동(켜면 KST 00/06/12/18 실배치+실과금).
