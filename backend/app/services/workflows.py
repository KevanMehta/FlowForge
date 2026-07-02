from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from ..models import Workflow, WorkflowEdge, WorkflowNode, WorkflowVersion
from ..schemas.common import WorkflowGraph
from .graph_validation import GraphValidationService


def graph_from_workflow(workflow: Workflow) -> WorkflowGraph:
    return WorkflowGraph(
        nodes=[{"id": n.node_key, "type": n.type, "label": n.label, "config": n.config, "position": n.position} for n in workflow.nodes],
        edges=[{"id": e.edge_key, "source": e.source_node_key, "target": e.target_node_key, "condition": e.condition} for e in workflow.edges],
    )


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db
        self.validator = GraphValidationService()

    def save_graph(self, workflow: Workflow, graph: WorkflowGraph) -> Workflow:
        self.db.execute(delete(WorkflowNode).where(WorkflowNode.workflow_id == workflow.id))
        self.db.execute(delete(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow.id))
        self.db.flush()
        for node in graph.nodes:
            self.db.add(WorkflowNode(workflow_id=workflow.id, node_key=node.id, type=node.type, label=node.label, config=node.config, position=node.position))
        for edge in graph.edges:
            self.db.add(WorkflowEdge(workflow_id=workflow.id, edge_key=edge.id, source_node_key=edge.source, target_node_key=edge.target, condition=edge.condition))
        return workflow

    def create_version(self, workflow: Workflow, graph: WorkflowGraph, user_id) -> WorkflowVersion:
        validation = self.validator.validate(graph)
        next_version = workflow.current_version + 1 if workflow.current_version else 1
        workflow.current_version = next_version
        version = WorkflowVersion(workflow_id=workflow.id, version=next_version, graph=graph.model_dump(), validation=validation.model_dump(), created_by_id=user_id)
        self.db.add(version)
        return version

    def latest_graph(self, workflow: Workflow) -> WorkflowGraph:
        return graph_from_workflow(workflow)

    def list_for_user(self, user) -> list[Workflow]:
        stmt = select(Workflow).order_by(Workflow.updated_at.desc())
        if user.role.name != "admin":
            stmt = stmt.where(Workflow.owner_id == user.id)
        return list(self.db.scalars(stmt))
