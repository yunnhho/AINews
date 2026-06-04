from typing import Literal

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_admin_user
from app.models.user import User
from app.services import admin as admin_svc

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/metrics")
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await admin_svc.get_metrics(db)


@router.get("/batches")
async def get_batches(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await admin_svc.get_batches(db)


@router.get("/sources/health")
async def get_sources_health(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await admin_svc.get_sources_health(db)


@router.patch("/sources/{source_id}")
async def toggle_source(
    source_id: int,
    enabled: bool = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await admin_svc.toggle_source(db, source_id, enabled)


@router.get("/translation-queue")
async def get_translation_queue(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await admin_svc.get_translation_queue(db)


@router.patch("/translation-queue/{log_id}")
async def handle_translation_review(
    log_id: int,
    action: Literal["approve", "reject"] = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await admin_svc.handle_translation_review(db, log_id, action)


@router.get("/costs/daily")
async def get_daily_costs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    return await admin_svc.get_daily_costs(db)
