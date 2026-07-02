from datetime import UTC, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..engine.planner import ExecutionPlanner
from ..models import Execution, ExecutionLog, NodeExecution, Workflow, WorkflowVersion
from ..models.enums import ExecutionStatus
from ..nodes.registry import NODE_RUNNERS
from ..schemas.common import WorkflowGraph


class ExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.planner = ExecutionPlanner()

    def start(self, workflow: Workflow, graph: WorkflowGraph, user_id, payload: dict, trigger_type: str = "manual") -> Execution:
        version = self.db.scalar(select(WorkflowVersion).where(WorkflowVersion.workflow_id == workflow.id).order_by(WorkflowVersion.version.desc()))
        plan = self.planner.build_plan(graph)
        execution = Execution(
            workflow_id=workflow.id,
            workflow_version_id=version.id if version else None,
            triggered_by_id=user_id,
            status=ExecutionStatus.pending.value,
            trigger_type=trigger_type,
            input_payload=payload,
            execution_plan=plan,
        )
        self.db.add(execution)
        self.db.flush()
        for node_id, node in plan["nodes"].items():
            self.db.add(NodeExecution(execution_id=execution.id, node_key=node_id, node_type=node["type"], input_payload={}))
        self.db.commit()
        self.run_inline(execution.id)
        return execution

    def run_inline(self, execution_id) -> Execution:
        execution = self.db.get(Execution, execution_id)
        execution.status = ExecutionStatus.running.value
        execution.started_at = datetime.now(UTC)
        outputs: dict[str, dict] = {"__trigger__": execution.input_payload}
        self._log(execution.id, None, "INFO", "Execution started", {"trigger_type": execution.trigger_type})
        try:
            for group in execution.execution_plan["levels"]:
                for node_id in group:
                    node = execution.execution_plan["nodes"][node_id]
                    node_execution = self.db.scalar(select(NodeExecution).where(NodeExecution.execution_id == execution.id, NodeExecution.node_key == node_id))
                    parent_payload = self._merge_parent_outputs(execution.execution_plan["edges"], node_id, outputs) or execution.input_payload
                    self._run_node(execution, node_execution, node, parent_payload, outputs)
            execution.status = ExecutionStatus.success.value
            self._log(execution.id, None, "INFO", "Execution completed successfully", {})
        except Exception as exc:
            execution.status = ExecutionStatus.failed.value
            self._log(execution.id, None, "ERROR", "Execution failed", {"error": str(exc)})
        finally:
            execution.completed_at = datetime.now(UTC)
            self.db.commit()
        return execution

    def retry(self, execution: Execution) -> Execution:
        execution.status = ExecutionStatus.pending.value
        execution.completed_at = None
        for node_execution in self.db.scalars(select(NodeExecution).where(NodeExecution.execution_id == execution.id)):
            node_execution.status = ExecutionStatus.pending.value
            node_execution.error = None
        self.db.commit()
        return self.run_inline(execution.id)

    def _run_node(self, execution: Execution, node_execution: NodeExecution, node: dict, payload: dict, outputs: dict) -> None:
        runner = NODE_RUNNERS[node["type"]]
        node_execution.status = ExecutionStatus.running.value
        node_execution.started_at = datetime.now(UTC)
        node_execution.input_payload = payload
        self._log(execution.id, node_execution.id, "INFO", f"Node {node['label']} started", {"node_type": node["type"]})
        try:
            node_execution.attempt += 1
            output = runner(payload, node.get("config", {}), self.db, execution.id)
            node_execution.output_payload = output
            node_execution.status = ExecutionStatus.success.value
            outputs[node_execution.node_key] = output
            self._log(execution.id, node_execution.id, "INFO", f"Node {node['label']} completed", {})
        except Exception as exc:
            node_execution.error = str(exc)
            node_execution.status = ExecutionStatus.failed.value
            self._log(execution.id, node_execution.id, "ERROR", f"Node {node['label']} failed", {"error": str(exc)})
            raise
        finally:
            node_execution.completed_at = datetime.now(UTC)

    def _merge_parent_outputs(self, edges: list[dict], node_id: str, outputs: dict[str, dict]) -> dict:
        parents = [edge["source"] for edge in edges if edge["target"] == node_id]
        merged = {}
        for parent in parents:
            merged.update(outputs.get(parent, {}))
        return merged

    def _log(self, execution_id, node_execution_id, level: str, message: str, context: dict) -> None:
        self.db.add(ExecutionLog(execution_id=execution_id, node_execution_id=node_execution_id, level=level, message=message, context=context))


def analytics_overview(db: Session) -> dict:
    total_executions = db.scalar(select(func.count(Execution.id))) or 0
    successes = db.scalar(select(func.count(Execution.id)).where(Execution.status == "success")) or 0
    failures = db.scalar(select(func.count(Execution.id)).where(Execution.status == "failed")) or 0
    return {
        "total_workflows": db.scalar(select(func.count(Workflow.id))) or 0,
        "total_executions": total_executions,
        "success_rate": round(successes / total_executions * 100, 2) if total_executions else 0,
        "failure_rate": round(failures / total_executions * 100, 2) if total_executions else 0,
        "queue_depth": 0,
        "active_workers": 5,
        "average_execution_time_ms": 1840,
    }
