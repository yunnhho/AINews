from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import push as push_svc

router = APIRouter(prefix="/v1/push", tags=["push"])


class DeviceRegisterRequest(BaseModel):
    expo_push_token: str = Field(..., description="ExponentPushToken[...] 형식")


class NotificationToggleRequest(BaseModel):
    expo_push_token: str
    enabled: bool


@router.post("/register", status_code=status.HTTP_204_NO_CONTENT)
async def register_device(
    body: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """디바이스 토큰 등록 — 중복 등록 자동 처리."""
    await push_svc.register_device(db, current_user.id, body.expo_push_token)
    await db.commit()


@router.patch("/notifications", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_notifications(
    body: NotificationToggleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """알림 ON/OFF 전환."""
    await push_svc.set_notifications_enabled(
        db, current_user.id, body.expo_push_token, body.enabled
    )
    await db.commit()
