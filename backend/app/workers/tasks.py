from sqlalchemy import select
from ..database import SessionLocal
from ..models import WorkerHeartbeat
from ..services.execution import ExecutionService
from .celery_app import celery_app


@celery_app.task(name="flowforge.execute_workflow")
def execute_workflow(execution_id: str) -> dict:
    with SessionLocal() as db:
        execution = ExecutionService(db).run_inline(execution_id)
        return {"execution_id": str(execution.id), "status": execution.status}


@celery_app.task(name="flowforge.worker_heartbeat")
def worker_heartbeat(worker_name: str = "flowforge-worker") -> dict:
    with SessionLocal() as db:
        heartbeat = db.scalar(select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == worker_name))
        if heartbeat:
            heartbeat.status = "online"
            heartbeat.metadata_json = {"utilization": 42}
        else:
            db.add(WorkerHeartbeat(worker_name=worker_name, metadata_json={"utilization": 42}))
        db.commit()
    return {"ok": True}
