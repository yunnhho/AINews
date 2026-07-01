# AI Pulse — 데모 배포 가이드 (DEPLOY.md)

공개 **읽기전용 라이브 데모**를 비용 0에 가깝게 띄우는 방법. 두 경로를 제공한다.

- **A. 로컬/단일 서버** — `docker compose up` 한 방 (권장, 가장 간단)
- **B. 무료·저가 호스팅** — 프론트 Vercel + 백엔드 Fly.io/Railway

> 데모 모드에서는 실제 Claude 크레딧이 **절대** 발생하지 않는다(이중 가드). 외부 소스도
> 호출하지 않고 고정 스냅샷을 쓴다. 모든 쓰기 요청은 403으로 차단된다.

---

## 0. 데모 모드 스위치 (공통)

`.env` (루트, 백엔드/워커용):

```bash
DEMO_MODE=true               # 재생 클라이언트 + 스냅샷 수집 + 쓰기 403 + Admin 읽기전용 공개
MONTHLY_BUDGET_USD=20        # 월 하드캡 $20 임박 연출 (머니샷3)
APP_ENV=production           # 문서(/docs) 비노출 등 운영 하드닝
SECRET_KEY=<32자+ 랜덤>       # openssl rand -hex 32
JWT_SECRET=<32자+ 랜덤>       # openssl rand -hex 32
ALLOWED_ORIGINS=https://<프론트 도메인>
ALLOWED_HOSTS=<백엔드 도메인>
COOKIE_SECURE=true
# ANTHROPIC_API_KEY 는 비워도 된다(재생 모드). 키가 있어도 DEMO_MODE=true면 호출 안 함.
```

프론트엔드 `.env` (Vercel 환경변수):

```bash
NEXT_PUBLIC_DEMO_MODE=true               # Admin 로그인 우회 + 쓰기 버튼 비활성 + 데모 배너
NEXT_PUBLIC_API_URL=https://<백엔드 도메인>/v1
```

### 이중 가드 요약 (비용 0 보장)
1. `DEMO_MODE=true` → 파이프라인이 `ReplayClient`로 대체 → 실제 API 호출 없음
2. `ANTHROPIC_API_KEY` 미설정 → **데모가 아니어도** 자동으로 재생(안전한 기본값)
   → 실제 호출은 `DEMO_MODE=false` **그리고** 키가 있을 때만 발생.

---

## A. docker compose (로컬 / 단일 VM)

```bash
# 1) 환경변수
cp .env.example .env
# .env 에서 위 "0. 데모 모드 스위치" 값 설정 (최소 DEMO_MODE=true, MONTHLY_BUDGET_USD=20)

# 2) 기동 (postgres·redis·es·api·worker·beat)
docker compose up -d --build

# 3) DB 마이그레이션
docker compose exec api alembic upgrade head

# 4) 결정적 시드 (머니샷 1~4 데이터, 몇 번 돌려도 같은 상태)
docker compose exec api python -m scripts.seed_demo

# 5) 프론트엔드 (별도)
cd frontend && npm ci && NEXT_PUBLIC_DEMO_MODE=true npm run build && npm start
```

- API: `http://localhost:8000`  · 프론트: `http://localhost:3000`
- Admin(읽기전용): `http://localhost:3000/admin`  (데모 모드라 로그인 불필요)
- (선택) 배치가 도는 모습을 직접 보이려면 — **무비용·오프라인**으로 실행된다:
  ```bash
  docker compose exec worker python -c "from pipeline.tasks.orchestrate import run_batch; run_batch(0)"
  ```

### 비용 0 유지 팁
- ES가 무거우면(512MB RAM) 데모에서 검색 머니샷을 스킵하고 `elasticsearch` 서비스를
  내려도 된다. 시드는 ES 없으면 색인만 건너뛴다(나머지는 정상).
- `beat`(스케줄러)를 꺼두면 자동 배치가 안 돈다. 데모는 시드 데이터만으로 충분하다.

---

## B. 무료·저가 호스팅 (프론트 Vercel + 백엔드 Fly.io/Railway)

목표: 상시 무료/최저가. Claude 비용은 재생 모드라 **$0**.

### B-1. 백엔드 — Fly.io (또는 Railway)
- 앱: `backend/`(FastAPI) — `fly launch` → `Dockerfile` 자동 인식
- 워커/비트는 데모에선 **생략 가능**(시드 데이터로 충분). 최소 비용을 원하면 `api`만 배포.
- 관리형 애드온:
  - Postgres: Fly Postgres(shared-cpu-1x 최소) 또는 Railway/Neon/Supabase 무료 티어
  - Redis: Upstash Redis 무료 티어 (`REDIS_URL`)
  - Elasticsearch: **선택**. 없으면 검색 머니샷만 스킵. 필요 시 Bonsai 무료 티어.
- 배포 후:
  ```bash
  fly ssh console -C "alembic upgrade head"
  fly ssh console -C "python -m scripts.seed_demo"
  ```
- 환경변수: 위 "0."의 백엔드 값 + `DATABASE_URL`/`REDIS_URL`/`ELASTICSEARCH_URL`.
  `scale count 1`, `auto_stop_machines=true`로 유휴 시 정지 → 사실상 $0.

### B-2. 프론트엔드 — Vercel
- 루트 `frontend/`, 프레임워크 Next.js 자동 인식.
- 환경변수: `NEXT_PUBLIC_DEMO_MODE=true`, `NEXT_PUBLIC_API_URL=https://<백엔드>/v1`
- 배포 후 백엔드 `ALLOWED_ORIGINS`에 Vercel 도메인 추가.

### 비용 0에 가깝게
| 항목 | 무료 옵션 |
|---|---|
| 프론트 | Vercel Hobby (무료) |
| 백엔드 | Fly.io free allowance / Railway 무료 크레딧, 유휴 자동정지 |
| Postgres | Neon / Supabase / Railway 무료 티어 |
| Redis | Upstash 무료 티어 |
| Elasticsearch | 생략(검색 머니샷 스킵) 또는 Bonsai 무료 |
| **Claude API** | **$0 (DEMO_MODE 재생)** |

---

## 공개 안전 체크리스트 (라이브 데모)
- [ ] `DEMO_MODE=true` (백엔드/워커) · `NEXT_PUBLIC_DEMO_MODE=true` (프론트)
- [ ] 모든 쓰기(POST/PATCH/DELETE) → 403 (`DemoModeMiddleware`) 확인
- [ ] Admin은 **읽기전용**만 (토글/승인/삭제 버튼 비활성)
- [ ] `APP_ENV=production` → `/docs`·`/openapi.json` 비노출
- [ ] `SECRET_KEY`·`JWT_SECRET` 기본값 아님(운영 부팅 가드가 강제)
- [ ] `ANTHROPIC_API_KEY`·OAuth 시크릿은 데모에 불필요 → 비워둔다
- [ ] 시드는 `python -m scripts.seed_demo` (멱등, 재실행 안전)

## 스모크 테스트
```bash
curl -s http://localhost:8000/v1/cards | head        # 피드(공개) 200
curl -s "http://localhost:8000/v1/search?q=검색"      # 한국어 검색 200
curl -s http://localhost:8000/v1/admin/metrics        # 데모모드 → 인증없이 200
curl -si -X POST http://localhost:8000/v1/cards/1/like | head -1          # 403 (쓰기 차단)
```
