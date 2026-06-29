from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    # 운영 TrustedHost 허용 호스트 (콤마 구분). 도메인 확정 시 .env에서 설정.
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,.aipulse.kr"
    # IP당 분당 요청 상한 (레이트리밋). 무한스크롤 피드를 막지 않도록 넉넉히.
    RATELIMIT_PER_MINUTE: int = 300
    # 인증 경로(/v1/auth) 전용 강한 레이트리밋 — 토큰/코드 brute-force 방어.
    AUTH_RATELIMIT_PER_MINUTE: int = 10
    # 앞단 신뢰 프록시(L7 LB 등) 홉 수. XFF 스푸핑 방어를 위해 끝에서 N번째를 클라이언트 IP로 본다.
    # 프록시 없이 직접 노출이면 0 (XFF 무시).
    TRUSTED_PROXY_COUNT: int = 0

    # 인증 쿠키 (웹). 운영에서는 COOKIE_SECURE=true, COOKIE_DOMAIN=.aipulse.kr 권장.
    COOKIE_DOMAIN: str = ""        # 비우면 호스트 전용 쿠키
    COOKIE_SECURE: bool = False    # 운영(HTTPS)에서 True
    COOKIE_SAMESITE: str = "lax"   # 동일 사이트(서브도메인)면 lax로 CSRF 1차 방어

    # DB
    DATABASE_URL: str = "postgresql+asyncpg://aipulse:aipulse@localhost:5432/aipulse"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # Claude
    ANTHROPIC_API_KEY: str = ""

    # GitHub
    GITHUB_TOKEN: str = ""

    # OAuth — Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/v1/auth/google/callback"

    # OAuth — GitHub
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/v1/auth/github/callback"

    # OAuth — Kakao
    KAKAO_CLIENT_ID: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = "http://localhost:8000/v1/auth/kakao/callback"

    # Expo Push
    EXPO_ACCESS_TOKEN: str = ""

    # JWT
    JWT_SECRET: str = "change-me"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Admin
    ADMIN_USER_IDS: str = ""
    MONTHLY_BUDGET_USD: float = 100.0

    # Alerts
    ALERT_SLACK_WEBHOOK_URL: str = ""
    ALERT_EMAIL_TO: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]

    @property
    def cookie_secure(self) -> bool:
        # 운영 환경에서는 명시 설정과 무관하게 항상 Secure 강제.
        return self.COOKIE_SECURE or self.APP_ENV == "production"

    @property
    def cookie_domain(self) -> str | None:
        return self.COOKIE_DOMAIN or None

    @property
    def admin_user_ids_list(self) -> list[int]:
        if not self.ADMIN_USER_IDS:
            return []
        return [int(uid.strip()) for uid in self.ADMIN_USER_IDS.split(",") if uid.strip().isdigit()]


settings = Settings()
