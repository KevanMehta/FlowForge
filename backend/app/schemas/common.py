from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: str = "developer"


class UserRead(ORMModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class NodeIn(BaseModel):
    id: str
    type: str
    label: str
    config: dict[str, Any] = {}
    position: dict[str, Any] = {}


class EdgeIn(BaseModel):
    id: str
    source: str
    target: str
    condition: str | None = None


class WorkflowGraph(BaseModel):
    nodes: list[NodeIn]
    edges: list[EdgeIn]


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = ""
    graph: WorkflowGraph


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    graph: WorkflowGraph | None = None


class WorkflowRead(ORMModel):
    id: str
    name: str
    description: str
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    graph: WorkflowGraph | None = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class ExecutionRead(ORMModel):
    id: str
    workflow_id: str
    status: str
    trigger_type: str
    started_at: datetime | None
    completed_at: datetime | None
    execution_plan: dict[str, Any]


class RunRequest(BaseModel):
    input_payload: dict[str, Any] = {}
    trigger_type: str = "manual"


class ScheduleCreate(BaseModel):
    workflow_id: str
    name: str
    cron: str | None = None
    run_at: datetime | None = None
    is_active: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    cron: str | None = None
    run_at: datetime | None = None
    is_active: bool | None = None
