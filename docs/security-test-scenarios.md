# AI Pulse — 보안 수정 테스트 시나리오

> `docs/security-audit.md`에서 수정한 인증·토큰·CSRF·레이트리밋 항목의 검증 절차.
> 자동 단위 테스트(인프라 비의존)는 `backend/tests/test_security.py`, 아래는 Redis/DB가 필요한
> 전 구간(E2E) 수동 검증이다.
>
> **사전 준비**: `docker compose up` (postgres/redis/es/backend/frontend 기동),
> OAuth 콘솔에 dev redirect_uri 등록. 아래 `$API`는 `http://localhost:8000/v1`.

---

## A. 자동 단위 테스트 (인프라 불필요)

```bash
cd backend && poetry install && poetry run pytest tests/test_security.py -v
```

검증 항목:
- access 토큰 발급/복호 라운드트립, 잘못된 타입·위조 토큰 거부
- OAuth URL이 platform이 아닌 **랜덤 state**를 싣는지
- `_client_ip`가 신뢰 프록시 없을 때 XFF 무시 / 있을 때 신뢰 홉 사용
- `set_auth_cookies`가 access/refresh=HttpOnly, csrf=비HttpOnly, refresh path=/v1/auth로 설정

> Python 3.12 + poetry 환경 필요. 현 개발 PC(전역 3.8)에서는 미실행 — CI/도커에서 실행.

---

## B. #1·#2 토큰이 URL/localStorage에 없는지 (HttpOnly 쿠키)

1. 브라우저로 `http://localhost:8000/v1/auth/google?platform=web` 접속 → 구글 로그인.
2. 콜백 후 프론트(`/auth/callback` → `/`)로 이동.
3. **검증**:
   - 주소창/히스토리/네트워크 리다이렉트 URL에 `access_token=`이 **없어야** 한다.
   - DevTools → Application → Cookies: `access_token`, `refresh_token`에 **HttpOnly ✓**,
     `csrf_token`은 HttpOnly **없음**.
   - Application → Local Storage `ai-pulse-auth`: `user`만 있고 **token 키 없음**.
   - Console에서 `document.cookie` → `csrf_token`만 보이고 access/refresh는 **안 보임**.

**기대**: 토큰은 JS로 접근 불가, URL 어디에도 노출 없음.

---

## C. #3 OAuth state(CSRF) 검증

```bash
# 위조/만료 state로 콜백 직접 호출
curl -i "$API/auth/google/callback?code=anything&state=forged-state"
```
**기대**: `401 UNAUTHORIZED` ("유효하지 않거나 만료된 인증 요청입니다."). 토큰 미발급.

- 정상 로그인 1회 후 동일 state 재사용 → state는 `getdel`로 소비되므로 두 번째는 401.

---

## D. 쿠키 인증 + CSRF 더블 서브밋

로그인 상태(쿠키 보유)에서:

```bash
# csrf 쿠키 값 확인 (브라우저 콘솔: document.cookie) → $CSRF 에 대입
# 1) CSRF 헤더 없이 좋아요(POST) → 차단
curl -i -X POST "$API/cards/1/like" \
  -H "Cookie: access_token=<복사>; csrf_token=<복사>"
# → 403 CSRF_FAILED

# 2) CSRF 헤더 일치 → 통과
curl -i -X POST "$API/cards/1/like" \
  -H "Cookie: access_token=<복사>; csrf_token=<복사>" \
  -H "X-CSRF-Token: <csrf_token과 동일값>"
# → 204
```
**기대**: 헤더 누락/불일치 시 403, 일치 시 정상. 브라우저 UI(좋아요·북마크·로그아웃)는 자동으로 헤더를 실어 정상 동작.

- **모바일(Bearer) 면제 확인**: `-H "Authorization: Bearer <access>"`로 같은 POST → CSRF 헤더 없이도 통과(쿠키 아님).

---

## E. #4 Refresh 회전 + 재사용 탐지

```bash
# 모바일 계약(JSON)으로 검증
R1=$(curl -s -X POST "$API/auth/exchange" -H "Content-Type: application/json" -d '{"code":"<일회용코드>"}')
RT=$(echo "$R1" | jq -r .refresh_token)

# 1) RT로 갱신 → 새 access/refresh
R2=$(curl -s -X POST "$API/auth/refresh" -H "Content-Type: application/json" -d "{\"refresh_token\":\"$RT\"}")
echo "$R2" | jq .

# 2) 같은 RT 재사용 → 거부(이미 회전되어 jti 소비됨)
curl -i -X POST "$API/auth/refresh" -H "Content-Type: application/json" -d "{\"refresh_token\":\"$RT\"}"
# → 401 "유효하지 않거나 폐기된 리프레시 토큰입니다."
```
**기대**: 회전 동작 + 재사용 탐지.

- **로그아웃 폐기**: 웹에서 로그아웃(DELETE `/auth/logout`) 후, 그 refresh로 갱신 시도 → 401.
- **웹 자동 갠신**: access 만료(60분) 후 보호 API 호출 시 프론트가 `/auth/refresh`로 조용히 재발급 후 1회 재시도 → 사용자 체감 무중단.

---

## F. #5·#6 레이트리밋

```bash
# 인증 경로는 분당 AUTH_RATELIMIT_PER_MINUTE(기본 10)
for i in $(seq 1 12); do curl -s -o /dev/null -w "%{http_code}\n" "$API/auth/refresh" -X POST; done
# → 앞 10개 통과/처리, 이후 429
```
**기대**: 11번째부터 `429 RATE_LIMITED`.

- **XFF 스푸핑 무력화 확인** (`TRUSTED_PROXY_COUNT=0` 기준):
```bash
for i in $(seq 1 12); do curl -s -o /dev/null -w "%{http_code}\n" \
  "$API/auth/refresh" -X POST -H "X-Forwarded-For: 1.2.3.$i"; done
# → IP를 위조해도 동일 버킷이라 11번째부터 429 (우회 불가)
```

---

## G. #7 CORS

```bash
# 허용 오리진 + 프리플라이트
curl -i -X OPTIONS "$API/cards/1/like" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-CSRF-Token"
# → 200, Access-Control-Allow-Origin: http://localhost:3000,
#   Allow-Methods에 POST, Allow-Headers에 X-CSRF-Token, Allow-Credentials: true

# 비허용 오리진
curl -i -X OPTIONS "$API/cards/1/like" -H "Origin: https://evil.example" \
  -H "Access-Control-Request-Method: POST"
# → Access-Control-Allow-Origin 헤더 없음(차단)
```

---

## H. 회귀 — 모바일 플로우 (변경 없음 확인)

1. `GET /auth/google?platform=mobile` → 콜백이 `aipulse://auth/callback?code=...`로 302.
2. `POST /auth/exchange {code}` → `{access_token, refresh_token, expires_in}` JSON.
3. `Authorization: Bearer <access>`로 `/auth/me`, `/me/bookmarks` 등 정상.

**기대**: 모바일은 기존과 동일하게 동작(Bearer 헤더, JSON 토큰).

---

## 통과 기준 요약
- B: URL·localStorage·JS 어디에도 토큰 없음 / 쿠키 HttpOnly
- C: 위조·재사용 state 401
- D: CSRF 헤더 없으면 403, 있으면 통과 / Bearer는 면제
- E: refresh 1회용 회전 + 재사용·로그아웃 후 401
- F: 인증 경로 분당 한도 초과 시 429 / XFF 위조로 우회 불가
- G: 허용 오리진만 CORS 통과
- H: 모바일 회귀 없음
