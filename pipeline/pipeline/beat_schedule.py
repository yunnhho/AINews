from celery.schedules import crontab

from pipeline.celery_app import app

# KST 00:00 / 06:00 / 12:00 / 18:00 (UTC+9 → UTC 15:00/21:00/03:00/09:00)
app.conf.beat_schedule = {
    "batch-00-kst": {
        "task": "pipeline.tasks.orchestrate.run_batch",
        "schedule": crontab(hour=15, minute=0),  # KST 00:00
        "kwargs": {"scheduled_hour": 0},
    },
    "batch-06-kst": {
        "task": "pipeline.tasks.orchestrate.run_batch",
        "schedule": crontab(hour=21, minute=0),  # KST 06:00
        "kwargs": {"scheduled_hour": 6},
    },
    "batch-12-kst": {
        "task": "pipeline.tasks.orchestrate.run_batch",
        "schedule": crontab(hour=3, minute=0),   # KST 12:00
        "kwargs": {"scheduled_hour": 12},
    },
    "batch-18-kst": {
        "task": "pipeline.tasks.orchestrate.run_batch",
        "schedule": crontab(hour=9, minute=0),   # KST 18:00
        "kwargs": {"scheduled_hour": 18},
    },
}
