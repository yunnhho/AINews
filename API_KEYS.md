# 외부 API 키 / 시크릿 정리

AI Pulse 운영에 필요한 **외부 발급 키**를 한곳에 정리한 문서입니다.
실제 값은 여기 적지 말고 `.env` 에만 보관하세요. (이 파일은 발급처·용도·필요 권한만 기록)

> 환경변수 전체 목록은 [`.env.example`](.env.example) 참고. 아래는 그중 **외부 서비스에서 직접 발급받아야 하는 항목**만 추렸습니다.

## 1. 외부에서 발급받아야 하는 키 (필수)

| 환경변수 | 용도 | 발급처 | 비고 |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API (요약·분류·번역) | https://console.anthropic.com/ → API Keys | `sk-ant-...` 형식. 사용량 과금 |
| `GITHUB_TOKEN` | 소스 그룹 B(GitHub) 수집 — Trending/Repo API | https://github.com/settings/tokens (PAT) | `ghp_...`. public repo 읽기 권한이면 충분 |

## 2. OAuth 소셜 로그인 (필수 — 로그인 기능 사용 시)

| 환경변수 | 용도 | 발급처 |
|---|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google 소셜 로그인 | https://console.cloud.google.com/ → APIs & Services → Credentials → OAuth 2.0 Client ID |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub 소셜 로그인 | https://github.com/settings/developers → OAuth Apps |
| `KAKAO_CLIENT_ID` / `KAKAO_CLIENT_SECRET` | Kakao 소셜 로그인 | https://developers.kakao.com/ → 내 애플리케이션 → 앱 키(REST API 키) / 보안 |
| `NEXT_PUBLIC_KAKAO_JS_KEY` | 프론트엔드 Kakao SDK (JavaScript 키) | 위 Kakao 앱 → 앱 키(JavaScript 키) |

> 각 OAuth 앱의 Redirect URI는 `*_REDIRECT_URI` 값과 발급처 콘솔 양쪽에 동일하게 등록해야 합니다.
> - Google: `http://localhost:8000/v1/auth/google/callback`
> - GitHub: `http://localhost:8000/v1/auth/github/callback`
> - Kakao:  `http://localhost:8000/v1/auth/kakao/callback`

## 3. 푸시 / 알림 / 메일 (선택)

| 환경변수 | 용도 | 발급처 |
|---|---|---|
| `EXPO_ACCESS_TOKEN` | Expo 푸시 알림 발송 | https://expo.dev/ → Account Settings → Access Tokens |
| `ALERT_SLACK_WEBHOOK_URL` | 배치 실패/알림 Slack 전송 | https://api.slack.com/messaging/webhooks (Incoming Webhook) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | 이메일 알림 발송 | 사용하는 메일 제공자(SES/Gmail SMTP/네이버웍스 등) |
| `IMAP_HOST` / `IMAP_USER` / `IMAP_PASSWORD` | 소스 그룹 D-2(뉴스레터 이메일) 수집 | 수집용 메일 계정의 IMAP 설정. Gmail은 앱 비밀번호 필요 |

## 4. 직접 생성하는 시크릿 (외부 발급 아님 — 운영 전 반드시 교체)

| 환경변수 | 용도 | 생성 방법 |
|---|---|---|
| `SECRET_KEY` | 앱 시크릿 | `openssl rand -hex 32` |
| `JWT_SECRET` | JWT 서명 키 | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | DB 비밀번호 | 임의의 강한 문자열 |

---

## 보안 주의사항

- **`.env` 는 절대 커밋하지 않습니다** (`.gitignore` 에 포함되어 있어야 함).
- 키가 노출되면 즉시 발급처에서 폐기(revoke) 후 재발급합니다.
- 프로덕션/개발 키를 분리하고, OAuth Redirect URI 도 환경별로 등록합니다.
- `NEXT_PUBLIC_*` 로 시작하는 값은 **브라우저에 노출**되므로 비밀키를 넣지 않습니다(공개 키만).
