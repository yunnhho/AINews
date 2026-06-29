# AI Pulse — 배포 전 보안 점검 (Security Audit)

> 배포 직전 인증·토큰·개인정보 노출 관점에서 백엔드/프론트엔드를 점검한 결과.
> 심각도순으로 정리하고, 각 항목의 **위치 → 문제 → 해결 방향 → 상태**를 기록한다.
>
> - 상태 표기: `🔴 TODO` / `🟡 진행중` / `✅ 완료` / `📝 수용(Accepted Risk)`
> - 수정은 위험도 높은 순으로 진행하며, 서로 영향을 주는 작업은 직렬, 독립 작업은 병렬로 처리한다.

점검일: 2026-06-29 · 수정 완료일: 2026-06-29

> **진행 결과 요약**: #1·#2·#3·#4·#5·#6·#7 수정 완료(✅), #8 수용(📝).
> 웹 인증을 **HttpOnly 쿠키 + 더블 서브밋 CSRF + refresh 회전**으로 전면 개편했고,
> 모바일(Bearer + 일회용 코드) 계약은 그대로 유지된다. 상세는 본문 하단 "구현 요약" 참조.

---

## 작업 순서 (의존성 그래프)

**직렬 체인 A — 인증 플로우 개편** (같은 콜백/의존성/프론트 파일을 공유하므로 순서대로)
1. #3 OAuth `state` CSRF 방어 + #1 토큰 URL 노출 제거 + #2 localStorage 제거
   → **HttpOnly 쿠키 기반**으로 통합 개편 (웹). 모바일은 기존 일회용 코드 유지.
2. #4 Refresh token 무효화·회전 (로그아웃/재발급) — 1번 위에서 진행

**병렬 그룹 B — 미들웨어/설정** (인증 로직과 파일이 겹치지 않음)
- #5 X-Forwarded-For 스푸핑으로 인한 레이트리밋 우회 (`middleware.py`)
- #6 인증 엔드포인트 강한 레이트리밋 (`middleware.py` / auth 라우터)
- #7 CORS 와일드카드 최소화 (`main.py`)

**문서/수용**
- #8 HS256 키 전략 — 현 단계 수용, 향후 과제로 기록

> 그룹 B의 #5·#6은 같은 `middleware.py`를 수정하므로 그 둘은 내부적으로 직렬,
> 그룹 A와 그룹 B는 서로 독립이라 병렬 처리 가능.

---

## 🔴 Critical

### #1. 웹 OAuth 콜백에서 `access_token`을 URL 쿼리스트링으로 전달
- **위치**: `backend/app/routers/auth.py` (kakao_callback / oauth_callback 웹 분기)
- **문제**: 토큰·user_id·nickname·avatar_url이 URL로 전달 → 브라우저 히스토리·Referer·서버/프록시 접근 로그·북마크에 평문 잔류 → 토큰 탈취 및 개인정보 노출.
- **해결**: 콜백에서 토큰을 URL이 아닌 **HttpOnly + Secure + SameSite 쿠키**로 설정. 사용자 식별 정보도 URL에서 제거하고 `/auth/me`로 조회.
- **상태**: ✅ 완료

### #2. JWT를 localStorage에 저장 (XSS 시 즉시 탈취)
- **위치**: `frontend/stores/auth.ts` (zustand `persist` 기본 저장소 = localStorage)
- **문제**: XSS 한 번이면 토큰 전체 유출. 프론트에 CSP 부재.
- **해결**: 토큰을 프론트가 저장/접근하지 않도록 HttpOnly 쿠키로 전환. 스토어는 사용자 프로필(비민감)만 보관. 모든 인증 fetch는 `credentials: 'include'`.
- **상태**: ✅ 완료

### #3. OAuth `state`에 CSRF 방어 nonce 없음
- **위치**: `backend/app/services/auth.py:get_oauth_redirect_url` (`state = platform`)
- **문제**: state를 platform 값으로만 사용, 콜백에서 무작위성/세션 바인딩 검증 없음 → 로그인 CSRF. 모바일 `aipulse://` 커스텀 스킴 가로채기 위험.
- **해결**: 랜덤 nonce를 Redis에 저장(platform 포함)하여 발급, 콜백에서 검증·소비. (PKCE는 모바일 후속 과제로 기록)
- **상태**: ✅ 완료

---

## 🟠 High

### #4. Refresh token 무효화·회전 불가 (로그아웃이 no-op)
- **위치**: `backend/app/routers/auth.py:logout` / `refresh`, `services/auth.py`
- **문제**: stateless라 유출된 refresh token을 만료(30일)까지 폐기 불가. 재발급 시 회전 없음.
- **해결**: refresh token에 `jti` 부여, Redis 화이트리스트로 관리. 로그아웃·재발급 시 기존 jti 무효화 + 새 토큰 회전.
- **상태**: ✅ 완료

### #5. 레이트리밋 X-Forwarded-For 스푸핑으로 우회
- **위치**: `backend/app/middleware.py:RateLimitMiddleware._client_ip`
- **문제**: XFF 첫 IP를 무조건 신뢰 → 매 요청 가짜 IP로 버킷 분산해 무력화.
- **해결**: 신뢰 프록시 홉 수(`TRUSTED_PROXY_COUNT`) 기준으로 XFF 뒤에서부터 실제 IP 추출. 프록시 없으면 `request.client.host`만 사용.
- **상태**: ✅ 완료

### #6. 인증 엔드포인트에 강한 레이트리밋 부재
- **위치**: `backend/app/middleware.py` / `routers/auth.py`
- **문제**: `/auth/exchange`·`/auth/refresh`·콜백이 전역 분당 300회와 동일 적용 + Redis 장애 시 fail-open → 코드/토큰 brute-force·콜백 남용.
- **해결**: `/v1/auth/` 경로에 분당 별도 강한 제한(예: 분당 10회) 적용.
- **상태**: ✅ 완료

---

## 🟡 Medium

### #7. CORS 와일드카드 + credentials
- **위치**: `backend/app/main.py` (`allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=True`)
- **문제**: origins는 명시적이라 치명적이진 않으나, 쿠키 인증 전환 시 메서드/헤더 최소화 권장.
- **해결**: 실제 사용하는 메서드/헤더만 화이트리스트.
- **상태**: ✅ 완료

### #8. HS256 대칭키 단일 시크릿, 키 회전(kid) 메커니즘 없음
- **위치**: `backend/app/services/auth.py`
- **문제**: 시크릿 노출 시 전체 토큰 위조 가능, 무중단 회전 불가.
- **해결 방향**: 향후 RS256 + kid 검토. 현재 시크릿은 환경변수로만 관리되고 운영 부팅 시 기본값을 차단하므로 **현 MVP 단계에서는 수용**.
- **상태**: 📝 수용 (향후 과제)

---

## ✅ 이미 잘 되어 있는 부분 (회귀 방지용 기록)
- 운영 환경 기본 시크릿(`change-me`) 부팅 차단 — `main.py`
- 운영 시 `/docs`·`/redoc`·`/openapi.json` 비활성화
- 보안 헤더(X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, API CSP, 운영 HSTS) — `middleware.py`
- generic 예외 핸들러가 내부 오류 메시지 마스킹 — `exceptions.py`
- `.env` gitignore 처리, 커밋된 시크릿 없음
- 일회용 인증 코드 5분 TTL + `getdel` 원자적 소비 — `services/auth.py`

---

## 구현 요약 (2026-06-29)

### 신규/변경 파일
| 파일 | 변경 |
|---|---|
| `backend/app/cookies.py` (신규) | access/refresh HttpOnly 쿠키 + csrf_token(더블 서브밋) set/clear 헬퍼 |
| `backend/app/config.py` | `AUTH_RATELIMIT_PER_MINUTE`, `TRUSTED_PROXY_COUNT`, `COOKIE_DOMAIN/SECURE/SAMESITE` + `cookie_secure`/`cookie_domain` 프로퍼티 |
| `backend/app/services/auth.py` | 랜덤 OAuth state 발급/소비(`create/consume_oauth_state`), `get_oauth_redirect_url(provider, state)`, refresh jti 발급/회전/폐기(`issue_refresh_token`/`rotate_refresh_token`/`revoke_refresh_token`), `_decode_payload` |
| `backend/app/routers/auth.py` | 콜백이 쿠키 설정 후 파라미터 없는 리다이렉트, `/refresh` 회전(웹=쿠키/모바일=본문), `/logout` 폐기+쿠키삭제, state 검증 |
| `backend/app/dependencies.py` | access token을 Bearer 헤더 **또는** `access_token` 쿠키에서 추출 |
| `backend/app/middleware.py` | `CsrfMiddleware`(쿠키 인증 unsafe 요청에 X-CSRF-Token 검증), `_client_ip` XFF 신뢰 프록시 기반, 인증 경로 별도 강한 레이트리밋 |
| `backend/app/main.py` | `CsrfMiddleware` 등록, CORS 메서드/헤더 화이트리스트 |
| `frontend/lib/api.ts` | `credentials:'include'` + non-safe 요청 CSRF 헤더 + 401 시 `/auth/refresh` 1회 자동 재시도, `fetchMe`/`logoutRequest`, token 인자 제거 |
| `frontend/lib/admin-api.ts` | 동일(쿠키+CSRF+refresh 재시도), token 인자 제거 |
| `frontend/stores/auth.ts` | 토큰 미저장, 비민감 프로필만 persist, `refreshUser()`(`/auth/me`)·서버 `logout()` |
| `frontend/app/auth/callback/page.tsx` | URL 토큰 파싱 제거 → `refreshUser()` 후 홈 이동 |
| 프론트 소비처(피드/북마크/추천/검색/카드액션/헤더/admin) | `token` → `user` 기반 인증 상태, api 호출 token 인자 제거 |

### 동작 원리 (왜 안전한가)
- 운영에서 `aipulse.kr`(프론트)·`api.aipulse.kr`(백)은 **동일 사이트**라 `SameSite=lax` 쿠키가 교차 사이트 POST에 실리지 않아 1차 CSRF 방어가 된다. 정상 fetch(동일 사이트)에는 정상 전송된다.
- 2차로 **더블 서브밋 CSRF 토큰**: 백엔드가 비-HttpOnly `csrf_token` 쿠키를 내려주고, 프론트가 이를 읽어 `X-CSRF-Token` 헤더로 되돌려보내면 미들웨어가 일치를 검증한다. 공격자 사이트는 다른 도메인의 csrf 쿠키를 읽지 못한다.
- access token은 HttpOnly라 **JS에서 접근 불가** → XSS로도 탈취 불가. refresh token은 `/v1/auth` 경로 한정으로 노출면을 줄였다.
- refresh는 **회전 + jti 화이트리스트**라, 탈취된 토큰을 재사용하면 정상 사용자의 jti가 이미 소비되어 강제 재로그인으로 이어진다(재사용 탐지).
- 모바일은 커스텀 스킴 가로채기를 막는 **PKCE 미적용** 상태로 일회용 코드(5분, getdel) 방식을 유지 → 후속 과제(아래).

### 운영 배포 체크리스트
- [ ] `APP_ENV=production`, `SECRET_KEY`/`JWT_SECRET` 강한 랜덤값
- [ ] `COOKIE_SECURE=true`, `COOKIE_DOMAIN=.aipulse.kr`, `COOKIE_SAMESITE=lax`
- [ ] `ALLOWED_ORIGINS`에 실제 프론트 오리진만, `ALLOWED_HOSTS`에 실제 호스트만
- [ ] LB/프록시 단수에 맞춰 `TRUSTED_PROXY_COUNT` 설정(직접 노출이면 0)
- [ ] OAuth 콘솔의 redirect_uri를 운영 백엔드 URL로 갱신
- [ ] 프론트 `NEXT_PUBLIC_API_URL`이 동일 사이트(api 서브도메인)인지 확인

### 남은 후속 과제
- 모바일 OAuth **PKCE** 적용(`aipulse://` 스킴 가로채기 방어)
- #8 JWT **RS256 + kid** 전환(무중단 키 회전)
- 프론트(Next.js) 응답에 **CSP** 헤더 적용(현재 API에만 적용)

## 테스트
- 테스트 시나리오 및 검증 절차는 `docs/security-test-scenarios.md` 참조.
