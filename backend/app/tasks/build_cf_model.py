"""CF 모델 재학습 수동 트리거 유틸리티.

pipeline Celery 브로커로 train_cf_model 태스크를 전송한다.
Admin API 또는 스크립트에서 호출하여 즉시 모델 재학습을 시작할 수 있다.
"""
from celery import Celery

from app.config import settings

_TASK_NAME = "pipeline.tasks.train_cf.train_cf_model"

_celery = Celery(broker=settings.CELERY_BROKER_URL)


def trigger_cf_model_rebuild() -> str:
    """CF 모델 재학습 태스크를 브로커에 전송하고 task ID를 반환한다."""
    result = _celery.send_task(_TASK_NAME)
    return result.id
