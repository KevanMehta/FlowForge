import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), index=True)
    role: Mapped[Role] = relationship()


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"
    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    owner: Mapped[User] = relationship()
    nodes: Mapped[list["WorkflowNode"]] = relationship(cascade="all,delete-orphan")
    edges: Mapped[list["WorkflowEdge"]] = relationship(cascade="all,delete-orphan")


class WorkflowVersion(Base, TimestampMixin):
    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version", name="uq_workflow_version"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    graph: Mapped[dict] = mapped_column(JSONB, default=dict)
    validation: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class WorkflowNode(Base, TimestampMixin):
    __tablename__ = "workflow_nodes"
    __table_args__ = (Index("ix_workflow_nodes_workflow_node_key", "workflow_id", "node_key", unique=True),)
    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    node_key: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(64), index=True)
    label: Mapped[str] = mapped_column(String(160))
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    position: Mapped[dict] = mapped_column(JSONB, default=dict)


class WorkflowEdge(Base, TimestampMixin):
    __tablename__ = "workflow_edges"
    __table_args__ = (Index("ix_workflow_edges_workflow_edge_key", "workflow_id", "edge_key", unique=True),)
    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    edge_key: Mapped[str] = mapped_column(String(120))
    source_node_key: Mapped[str] = mapped_column(String(120), index=True)
    target_node_key: Mapped[str] = mapped_column(String(120), index=True)
    condition: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Execution(Base, TimestampMixin):
    __tablename__ = "executions"
    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    workflow_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workflow_versions.id"), nullable=True)
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    trigger_type: Mapped[str] = mapped_column(String(64), default="manual")
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    execution_plan: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NodeExecution(Base, TimestampMixin):
    __tablename__ = "node_executions"
    __table_args__ = (Index("ix_node_execution_execution_node", "execution_id", "node_key", unique=True),)
    id: Mapped[uuid.UUID] = uuid_pk()
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), index=True)
    node_key: Mapped[str] = mapped_column(String(120))
    node_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutionLog(Base, TimestampMixin):
    __tablename__ = "execution_logs"
    id: Mapped[uuid.UUID] = uuid_pk()
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), index=True)
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("node_executions.id"), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(20), default="INFO", index=True)
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)


class ExecutionArtifact(Base, TimestampMixin):
    __tablename__ = "execution_artifacts"
    id: Mapped[uuid.UUID] = uuid_pk()
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), index=True)
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("node_executions.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    artifact_type: Mapped[str] = mapped_column(String(40))
    content: Mapped[dict] = mapped_column(JSONB, default=dict)


class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"
    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(160))
    cron: Mapped[str | None] = mapped_column(String(80), nullable=True)
    run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkerHeartbeat(Base, TimestampMixin):
    __tablename__ = "worker_heartbeats"
    id: Mapped[uuid.UUID] = uuid_pk()
    worker_name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    queue_name: Mapped[str] = mapped_column(String(80), default="celery")
    status: Mapped[str] = mapped_column(String(32), default="online", index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = uuid_pk()
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(80), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(255), unique=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeadLetterTask(Base, TimestampMixin):
    __tablename__ = "dead_letter_tasks"
    id: Mapped[uuid.UUID] = uuid_pk()
    execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("executions.id"), nullable=True, index=True)
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("node_executions.id"), nullable=True)
    task_name: Mapped[str] = mapped_column(String(160), index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class NotificationEvent(Base, TimestampMixin):
    __tablename__ = "notification_events"
    id: Mapped[uuid.UUID] = uuid_pk()
    execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("executions.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(40), index=True)
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255), default="")
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="sent", index=True)


class SystemMetric(Base, TimestampMixin):
    __tablename__ = "system_metrics"
    id: Mapped[uuid.UUID] = uuid_pk()
    metric_name: Mapped[str] = mapped_column(String(120), index=True)
    metric_value: Mapped[float] = mapped_column(Numeric(18, 6))
    labels: Mapped[dict] = mapped_column(JSONB, default=dict)
