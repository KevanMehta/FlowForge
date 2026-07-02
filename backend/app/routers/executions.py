from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import current_user, require_roles
from ..models import Execution, ExecutionArtifact, ExecutionLog, NodeExecution, User, Workflow
from ..services.execution import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])


def can_view(user: User, execution: Execution, db: Session) -> bool:
    if user.role.name == "admin":
        return True
    workflow = db.get(Workflow, execution.workflow_id)
    return workflow is not None and workflow.owner_id == user.id


@router.get("")
def list_executions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Execution).order_by(Execution.created_at.desc()).limit(100)
    rows = list(db.scalars(stmt))
    return [
        {"id": str(e.id), "workflow_id": str(e.workflow_id), "status": e.status, "trigger_type": e.trigger_type, "started_at": e.started_at, "completed_at": e.completed_at}
        for e in rows
        if can_view(user, e, db)
    ]


@router.get("/{execution_id}")
def get_execution(execution_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    execution = db.get(Execution, execution_id)
    if not execution or not can_view(user, execution, db):
        raise HTTPException(status_code=404, detail="Execution not found")
    nodes = db.scalars(select(NodeExecution).where(NodeExecution.execution_id == execution.id).order_by(NodeExecution.created_at)).all()
    return {
        "id": str(execution.id),
        "workflow_id": str(execution.workflow_id),
        "status": execution.status,
        "trigger_type": execution.trigger_type,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "execution_plan": execution.execution_plan,
        "nodes": [{"id": str(n.id), "node_key": n.node_key, "node_type": n.node_type, "status": n.status, "attempt": n.attempt, "error": n.error, "started_at": n.started_at, "completed_at": n.completed_at} for n in nodes],
    }


@router.post("/{execution_id}/cancel")
def cancel_execution(execution_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    execution = db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    execution.status = "cancelled"
    db.commit()
    return {"ok": True}


@router.post("/{execution_id}/retry")
def retry_execution(execution_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    execution = db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    result = ExecutionService(db).retry(execution)
    return {"id": str(result.id), "status": result.status}


@router.get("/{execution_id}/logs")
def logs(execution_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    execution = db.get(Execution, execution_id)
    if not execution or not can_view(user, execution, db):
        raise HTTPException(status_code=404, detail="Execution not found")
    return [
        {"id": str(log.id), "level": log.level, "message": log.message, "context": log.context, "created_at": log.created_at}
        for log in db.scalars(select(ExecutionLog).where(ExecutionLog.execution_id == execution.id).order_by(ExecutionLog.created_at))
    ]


@router.get("/{execution_id}/timeline")
def timeline(execution_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    execution = db.get(Execution, execution_id)
    if not execution or not can_view(user, execution, db):
        raise HTTPException(status_code=404, detail="Execution not found")
    return [{"node_key": n.node_key, "node_type": n.node_type, "status": n.status, "attempt": n.attempt, "started_at": n.started_at, "completed_at": n.completed_at} for n in db.scalars(select(NodeExecution).where(NodeExecution.execution_id == execution.id).order_by(NodeExecution.created_at))]


@router.get("/{execution_id}/artifacts")
def artifacts(execution_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    execution = db.get(Execution, execution_id)
    if not execution or not can_view(user, execution, db):
        raise HTTPException(status_code=404, detail="Execution not found")
    return [{"id": str(a.id), "name": a.name, "artifact_type": a.artifact_type, "content": a.content, "created_at": a.created_at} for a in db.scalars(select(ExecutionArtifact).where(ExecutionArtifact.execution_id == execution.id))]
