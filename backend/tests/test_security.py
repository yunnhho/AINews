"""보안 수정에 대한 인프라 비의존(순수 로직) 단위 테스트.

Redis/DB/ES 없이 도는 부분만 검증한다. 실행: `cd backend && poetry install && poetry run pytest`
(Python 3.12 환경 필요. state/refresh 회전 등 Redis 의존 시나리오는
docs/security-test-scenarios.md의 수동 E2E 절차로 검증한다.)
"""
import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.cookies import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE, set_auth_cookies
from app.exceptions import UnauthorizedError
from app.middleware import RateLimitMiddleware
from app.services import auth as auth_svc


def _request(headers: dict | None = None, client=("1.2.3.4", 0)) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": client,
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
    }
    return Request(scope)


# ── JWT (access) ──────────────────────────────────────────────────────────────

def test_access_token_roundtrip():
    token = auth_svc.create_access_token(42)
    assert auth_svc.decode_token(token) == 42


def test_decode_rejects_wrong_type():
    # access 토큰을 refresh로 검증하면 거부되어야 한다.
    token = auth_svc.create_access_token(1)
    with pytest.raises(UnauthorizedError):
        auth_svc.decode_token(token, expected_type="refresh")


def test_decode_rejects_tampered():
    with pytest.raises(UnauthorizedError):
        auth_svc.decode_token("not.a.valid.jwt")


# ── OAuth state (CSRF) ─────────────────────────────────────────────────────────

def test_oauth_url_carries_random_state_not_platform():
    url = auth_svc.get_oauth_redirect_url("google", "RANDOM_STATE_XYZ")
    assert "state=RANDOM_STATE_XYZ" in url
    # 과거처럼 platform 문자열을 state로 노출하지 않는다.
    assert "state=web" not in url and "state=mobile" not in url


# ── 레이트리밋 IP 추출 (XFF 스푸핑 방어) ────────────────────────────────────────

def test_client_ip_ignores_xff_when_no_trusted_proxy(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_COUNT", 0)
    req = _request({"x-forwarded-for": "9.9.9.9"}, client=("1.2.3.4", 0))
    # 신뢰 프록시가 없으면 위조 가능한 XFF를 무시하고 직접 연결 IP를 쓴다.
    assert RateLimitMiddleware._client_ip(req) == "1.2.3.4"


def test_client_ip_uses_trusted_hop(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_COUNT", 1)
    # 공격자가 첫 항목을 위조해도, 끝에서 1번째(신뢰 프록시가 본 실제 IP)를 쓴다.
    req = _request({"x-forwarded-for": "1.1.1.1, 7.7.7.7"}, client=("10.0.0.1", 0))
    assert RateLimitMiddleware._client_ip(req) == "7.7.7.7"


# ── 인증 쿠키 플래그 ────────────────────────────────────────────────────────────

def test_set_auth_cookies_flags():
    resp = Response()
    csrf = set_auth_cookies(resp, "access-token-value", "refresh-token-value")
    assert csrf  # CSRF 토큰 반환

    cookies = resp.headers.getlist("set-cookie")
    by_name = {c.split("=", 1)[0]: c for c in cookies}

    assert ACCESS_COOKIE in by_name and REFRESH_COOKIE in by_name and CSRF_COOKIE in by_name
    # access/refresh는 HttpOnly여야 한다(JS 접근 차단).
    assert "httponly" in by_name[ACCESS_COOKIE].lower()
    assert "httponly" in by_name[REFRESH_COOKIE].lower()
    # csrf 쿠키는 프론트가 읽어야 하므로 HttpOnly가 아니어야 한다.
    assert "httponly" not in by_name[CSRF_COOKIE].lower()
    # refresh 쿠키는 /v1/auth 경로로 노출면을 줄인다.
    assert "path=/v1/auth" in by_name[REFRESH_COOKIE].lower()
