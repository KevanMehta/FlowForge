from enum import Enum


class RoleName(str, Enum):
    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class WorkflowStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class ExecutionStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"
    partial = "partial"
    skipped = "skipped"


class NodeType(str, Enum):
    webhook_trigger = "webhook_trigger"
    manual_trigger = "manual_trigger"
    schedule_trigger = "schedule_trigger"
    validate_json = "validate_json"
    http_request = "http_request"
    transform_data = "transform_data"
    ai_summarizer = "ai_summarizer"
    ai_classifier = "ai_classifier"
    ai_json_generator = "ai_json_generator"
    conditional_branch = "conditional_branch"
    delay = "delay"
    email_notification = "email_notification"
    slack_notification = "slack_notification"
    report_generator = "report_generator"
