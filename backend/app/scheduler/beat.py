from ..workers.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "worker-heartbeat-every-minute": {
        "task": "flowforge.worker_heartbeat",
        "schedule": 60.0,
        "args": ("flowforge-beat",),
    }
}
