import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready
from kombu import Exchange, Queue

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

app = Celery(
    "ai_pulse",
    broker=broker_url,
    backend=result_backend,
    include=[
        "pipeline.tasks.orchestrate",
        "pipeline.tasks.check_source_health",
        "pipeline.tasks.train_cf",
        "pipeline.tasks.send_push",
    ],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_routes={
        "pipeline.tasks.orchestrate.*": {"queue": "batch"},
    },
    task_queues=(
        Queue("batch", Exchange("batch"), routing_key="batch"),
        Queue("default", Exchange("default"), routing_key="default"),
    ),
    task_default_queue="default",
    # KST 00/06/12/18시 배치 스케줄
    beat_schedule={
        "batch-00-kst": {
            "task": "pipeline.tasks.orchestrate.run_batch",
            "schedule": crontab(hour=15, minute=0),
            "kwargs": {"scheduled_hour": 0},
        },
        "batch-06-kst": {
            "task": "pipeline.tasks.orchestrate.run_batch",
            "schedule": crontab(hour=21, minute=0),
            "kwargs": {"scheduled_hour": 6},
        },
        "batch-12-kst": {
            "task": "pipeline.tasks.orchestrate.run_batch",
            "schedule": crontab(hour=3, minute=0),
            "kwargs": {"scheduled_hour": 12},
        },
        "batch-18-kst": {
            "task": "pipeline.tasks.orchestrate.run_batch",
            "schedule": crontab(hour=9, minute=0),
            "kwargs": {"scheduled_hour": 18},
        },
        # CF 모델 일 1회 재학습 — KST 02:00 (UTC 17:00), 자정 배치 이후
        "train-cf-model-daily": {
            "task": "pipeline.tasks.train_cf.train_cf_model",
            "schedule": crontab(hour=17, minute=0),  # KST 02:00
        },
    },
)


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    # sentence-transformers 모델 사전 로딩 (cold start 방지)
    try:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
        SentenceTransformer(model_name)
    except Exception as e:
        print(f"[worker_ready] sentence-transformers 로드 실패: {e}")
