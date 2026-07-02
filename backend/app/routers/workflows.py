from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import current_user, require_roles
from ..models import User, Workflow, WorkflowVersion
from ..schemas.common import RunRequest, WorkflowCreate, WorkflowGraph, WorkflowUpdate
from ..services.audit import audit
from ..services.execution import ExecutionService
from ..services.graph_validation import GraphValidationService
from ..services.workflows import WorkflowService, graph_from_workflow

router = APIRouter(prefix="/workflows", tags=["workflows"])


def serialize(workflow: Workflow) -> dict:
    return {"id": str(workflow.id), "name": workflow.name, "description": workflow.description, "status": workflow.status, "current_version": workflow.current_version, "created_at": workflow.created_at, "updated_at": workflow.updated_at, "graph": graph_from_workflow(workflow).model_dump()}


@router.post("")
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    validation = GraphValidationService().validate(payload.graph)
    if not validation.valid:
        raise HTTPException(status_code=422, detail=validation.errors)
    workflow = Workflow(owner_id=user.id, name=payload.name, description=payload.description)
    db.add(workflow)
    db.flush()
    service = WorkflowService(db)
    service.save_graph(workflow, payload.graph)
    service.create_version(workflow, payload.graph, user.id)
    audit(db, user, "workflow.create", "workflow", str(workflow.id))
    db.commit()
    db.refresh(workflow)
    return serialize(workflow)


@router.get("")
def list_workflows(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [serialize(w) for w in WorkflowService(db).list_for_user(user)]


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    workflow = db.get(Workflow, workflow_id)
    if not workflow or (user.role.name != "admin" and workflow.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return serialize(workflow)


@router.put("/{workflow_id}")
def update_workflow(workflow_id: str, payload: WorkflowUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if payload.name is not None:
        workflow.name = payload.name
    if payload.description is not None:
        workflow.description = payload.description
    service = WorkflowService(db)
    if payload.graph:
        validation = GraphValidationService().validate(payload.graph)
        if not validation.valid:
            raise HTTPException(status_code=422, detail=validation.errors)
        service.save_graph(workflow, payload.graph)
        service.create_version(workflow, payload.graph, user.id)
    audit(db, user, "workflow.update", "workflow", workflow_id)
    db.commit()
    return serialize(workflow)


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.status = "archived"
    audit(db, user, "workflow.archive", "workflow", workflow_id)
    db.commit()
    return {"ok": True}


@router.post("/{workflow_id}/validate")
def validate_workflow(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return GraphValidationService().validate(graph_from_workflow(workflow))


@router.post("/{workflow_id}/publish")
def publish_workflow(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.status = "published"
    audit(db, user, "workflow.publish", "workflow", workflow_id)
    db.commit()
    return serialize(workflow)


@router.get("/{workflow_id}/versions")
def versions(workflow_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [{"id": str(v.id), "version": v.version, "validation": v.validation, "created_at": v.created_at} for v in db.scalars(select(WorkflowVersion).where(WorkflowVersion.workflow_id == workflow_id).order_by(WorkflowVersion.version.desc()))]


@router.post("/{workflow_id}/rollback/{version_id}")
def rollback(workflow_id: str, version_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    workflow = db.get(Workflow, workflow_id)
    version = db.get(WorkflowVersion, version_id)
    if not workflow or not version:
        raise HTTPException(status_code=404, detail="Workflow or version not found")
    graph = WorkflowGraph.model_validate(version.graph)
    WorkflowService(db).save_graph(workflow, graph)
    workflow.current_version = version.version
    audit(db, user, "workflow.rollback", "workflow", workflow_id, {"version_id": version_id})
    db.commit()
    return serialize(workflow)


@router.post("/{workflow_id}/run")
def run_workflow(workflow_id: str, payload: RunRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "developer"))):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    execution = ExecutionService(db).start(workflow, graph_from_workflow(workflow), user.id, payload.input_payload, payload.trigger_type)
    audit(db, user, "execution.start", "execution", str(execution.id))
    db.commit()
    return {"id": str(execution.id), "status": execution.status}
