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
