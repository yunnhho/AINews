from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_admin_user
from app.models.user import User
from app.services import alerting as alerting_svc

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/alerts")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await alerting_svc.get_alert_history(db)


@router.post("/alerts/test")
async def test_alert(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await alerting_svc.send_test_alert(db)
