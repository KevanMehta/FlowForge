from celery import Celery
from ..config import get_settings

settings = get_settings()
celery_app = Celery("flowforge", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, worker_prefetch_multiplier=1, task_acks_late=True, timezone="UTC")
