from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserProfile(BaseModel):
    id: int
    provider: str
    nickname: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class AuthCodeExchangeRequest(BaseModel):
    code: str


class RefreshTokenRequest(BaseModel):
    # 웹은 쿠키로 받으므로 모바일(본문) 전용. 비어 있으면 쿠키를 사용한다.
    refresh_token: str | None = None
