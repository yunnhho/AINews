"""Expo Push Notification 서비스."""
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user_device import UserDevice

logger = logging.getLogger(__name__)

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def register_device(db: AsyncSession, user_id: int, expo_push_token: str) -> UserDevice:
    """디바이스 토큰 저장 — 중복 토큰은 user_id 갱신."""
    result = await db.execute(
        select(UserDevice).where(UserDevice.expo_push_token == expo_push_token)
    )
    device = result.scalar_one_or_none()

    if device is None:
        device = UserDevice(user_id=user_id, expo_push_token=expo_push_token)
        db.add(device)
    else:
        device.user_id = user_id
        device.notifications_enabled = True
        device.updated_at = datetime.now(UTC)

    await db.flush()
    return device


async def set_notifications_enabled(
    db: AsyncSession, user_id: int, expo_push_token: str, enabled: bool
) -> None:
    await db.execute(
        update(UserDevice)
        .where(
            UserDevice.user_id == user_id,
            UserDevice.expo_push_token == expo_push_token,
        )
        .values(notifications_enabled=enabled, updated_at=datetime.now(UTC))
    )


async def get_enabled_tokens(db: AsyncSession) -> list[str]:
    """알림 활성화된 모든 디바이스 토큰 반환."""
    result = await db.execute(
        select(UserDevice.expo_push_token).where(UserDevice.notifications_enabled.is_(True))
    )
    return list(result.scalars().all())


async def send_batch_complete_notification(tokens: list[str], news_count: int, tech_count: int) -> None:
    """배치 완료 후 Expo Push API로 알림 발송."""
    if not tokens:
        return

    total = news_count + tech_count
    body = f"뉴스 {news_count}건, 기술 {tech_count}건 업데이트"

    messages = [
        {
            "to": token,
            "title": f"AI Pulse — 새 카드 {total}건",
            "body": body,
            "sound": "default",
            "data": {"news_count": news_count, "tech_count": tech_count},
        }
        for token in tokens
    ]

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
    }
    if settings.EXPO_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_EXPO_PUSH_URL, json=messages, headers=headers)
            resp.raise_for_status()
            logger.info(f"푸시 알림 발송 완료: {len(tokens)}개 디바이스")
    except Exception as exc:
        logger.error(f"Expo Push API 발송 실패: {exc}", exc_info=True)
