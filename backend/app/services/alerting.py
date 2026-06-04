import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.batch import AlertLog, BatchLog, SourceHealth, TranslationLog
from app.redis import get_redis

# alert_type별 쿨다운 (초)
_COOLDOWN_TTLS: dict[str, int] = {
    "source_failure": 3600,
    "zero_collection": 3600,
    "low_translation_rate": 86400,
    "test": 0,
}


async def _is_in_cooldown(alert_type: str, source_name: str | None, redis=None) -> bool:
    if redis is None:
        redis = await get_redis()
    key = f"alert_cooldown:{alert_type}:{source_name or 'global'}"
    return bool(await redis.exists(key))


async def _set_cooldown(alert_type: str, source_name: str | None, redis=None) -> None:
    ttl = _COOLDOWN_TTLS.get(alert_type, 3600)
    if ttl == 0:
        return
    if redis is None:
        redis = await get_redis()
    key = f"alert_cooldown:{alert_type}:{source_name or 'global'}"
    await redis.setex(key, ttl, "1")


async def _send_slack(message: str) -> bool:
    if not settings.ALERT_SLACK_WEBHOOK_URL:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.ALERT_SLACK_WEBHOOK_URL, json={"text": message})
            return resp.status_code == 200
    except Exception:
        return False


def _send_email_sync(subject: str, body: str) -> bool:
    if not settings.SMTP_HOST or not settings.ALERT_EMAIL_TO or not settings.SMTP_USER:
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ALERT_EMAIL_TO
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, settings.ALERT_EMAIL_TO, msg.as_string())
        return True
    except Exception:
        return False


async def _send_email(subject: str, body: str) -> bool:
    return await asyncio.to_thread(_send_email_sync, subject, body)


async def send_alert(
    db: AsyncSession,
    alert_type: str,
    message: str,
    source_name: str | None = None,
    *,
    force: bool = False,
    redis=None,
) -> bool:
    if not force and await _is_in_cooldown(alert_type, source_name, redis):
        return False

    slack_ok = await _send_slack(f"[AI Pulse] {message}")
    email_ok = await _send_email(f"[AI Pulse Alert] {alert_type}", message)

    db.add(AlertLog(
        alert_type=alert_type,
        source_name=source_name,
        message=message,
        sent_via={"slack": slack_ok, "email": email_ok},
    ))
    await db.commit()
    await _set_cooldown(alert_type, source_name, redis)
    return True


async def check_and_alert(db: AsyncSession, redis=None) -> None:
    # ① 연속 실패 3회 이상 소스
    sources = (await db.execute(
        select(SourceHealth).where(SourceHealth.consecutive_failures >= 3)
    )).scalars().all()
    for s in sources:
        msg = f"소스 '{s.source_name}' 연속 {s.consecutive_failures}회 실패. 마지막 오류: {s.last_error_log}"
        await send_alert(db, "source_failure", msg, source_name=s.source_name, redis=redis)

    # ② 최근 배치 전체 수집 0건
    last_batch = (await db.execute(
        select(BatchLog).order_by(BatchLog.scheduled_at.desc()).limit(1)
    )).scalar_one_or_none()
    if last_batch and last_batch.collected_by_group is not None:
        if sum(last_batch.collected_by_group.values()) == 0:
            msg = f"배치 {last_batch.batch_id}: 전체 소스 수집 0건"
            await send_alert(db, "zero_collection", msg, redis=redis)

    # ③ 번역 통과율 < 70% (최근 100건, 일 1회)
    recent = (await db.execute(
        select(TranslationLog.passed)
        .order_by(TranslationLog.created_at.desc())
        .limit(100)
    )).scalars().all()
    if recent:
        rate = sum(1 for p in recent if p) / len(recent)
        if rate < 0.7:
            msg = f"번역 통과율 {rate:.1%} (최근 {len(recent)}건) — 임계값 70% 미달"
            await send_alert(db, "low_translation_rate", msg, redis=redis)


async def get_alert_history(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(AlertLog).order_by(AlertLog.created_at.desc()).limit(100)
    )).scalars().all()
    return {
        "items": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "source_name": a.source_name,
                "message": a.message,
                "sent_via": a.sent_via,
                "created_at": a.created_at.isoformat(),
            }
            for a in rows
        ]
    }


async def send_test_alert(db: AsyncSession, redis=None) -> dict:
    await send_alert(
        db,
        alert_type="test",
        message="AI Pulse 알림 시스템 테스트입니다.",
        redis=redis,
        force=True,
    )
    return {"status": "sent"}
