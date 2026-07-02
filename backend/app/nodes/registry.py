import json
import time
import httpx
from sqlalchemy.orm import Session
from ..models import ExecutionArtifact, NotificationEvent


class NodeExecutionError(RuntimeError):
    pass


def _text(payload: dict, config: dict) -> str:
    field = config.get("field", "text")
    return str(payload.get(field) or payload.get("text") or payload)


def summarize(payload: dict, config: dict, db: Session, execution_id) -> dict:
    text = _text(payload, config)
    words = text.split()
    return {"summary": " ".join(words[: min(28, len(words))]), "source_length": len(text)}


def classify(payload: dict, config: dict, db: Session, execution_id) -> dict:
    text = _text(payload, config).lower()
    categories = config.get("categories", ["general"])
    winner = max(categories, key=lambda c: text.count(str(c).lower()))
    return {"category": winner, "confidence": 0.86 if winner.lower() in text else 0.52}


def generate_json(payload: dict, config: dict, db: Session, execution_id) -> dict:
    fields = config.get("fields", ["title", "summary"])
    text = _text(payload, config)
    return {"json": {field: (text[:120] if field != "word_count" else len(text.split())) for field in fields}}


def validate_json(payload: dict, config: dict, db: Session, execution_id) -> dict:
    schema = config.get("schema", {})
    missing = [field for field in schema.get("required", []) if field not in payload]
    if missing:
        raise NodeExecutionError(f"Payload missing required fields: {', '.join(missing)}")
    return {"valid": True, "payload": payload}


def http_request(payload: dict, config: dict, db: Session, execution_id) -> dict:
    method = config.get("method", "GET").upper()
    url = config["url"]
    timeout = float(config.get("timeout", 5))
    with httpx.Client(timeout=timeout) as client:
        response = client.request(method, url, headers=config.get("headers"), json=config.get("body") or payload if method == "POST" else None)
    return {"status_code": response.status_code, "body": response.text[:2000]}


def transform_data(payload: dict, config: dict, db: Session, execution_id) -> dict:
    mapping = config.get("mapping", {})
    transformed = {target: payload.get(source, default) for target, source_default in mapping.items() for source, default in [source_default if isinstance(source_default, list) else (source_default, None)]}
    return transformed or payload


def conditional_branch(payload: dict, config: dict, db: Session, execution_id) -> dict:
    field = config.get("field", "status")
    equals = config.get("equals", "ok")
    return {"branch": "true" if str(payload.get(field)) == str(equals) else "false", "payload": payload}


def delay(payload: dict, config: dict, db: Session, execution_id) -> dict:
    seconds = min(float(config.get("seconds", 1)), 5)
    time.sleep(seconds)
    return {"delayed_seconds": seconds, "payload": payload}


def email_notification(payload: dict, config: dict, db: Session, execution_id) -> dict:
    event = NotificationEvent(execution_id=execution_id, channel="email", recipient=config["recipient"], subject=config.get("subject", "FlowForge notification"), body=json.dumps(payload))
    db.add(event)
    return {"notification": "email", "recipient": config["recipient"], "status": "sent"}


def slack_notification(payload: dict, config: dict, db: Session, execution_id) -> dict:
    event = NotificationEvent(execution_id=execution_id, channel="slack", recipient=config["channel"], subject="Slack notification", body=json.dumps(payload))
    db.add(event)
    return {"notification": "slack", "channel": config["channel"], "status": "sent"}


def report_generator(payload: dict, config: dict, db: Session, execution_id) -> dict:
    content = {"markdown": f"# {config.get('title', 'Workflow Report')}\n\n```json\n{json.dumps(payload, indent=2)}\n```"}
    db.add(ExecutionArtifact(execution_id=execution_id, name=config.get("title", "report.md"), artifact_type="markdown", content=content))
    return content


def pass_through(payload: dict, config: dict, db: Session, execution_id) -> dict:
    return payload


NODE_RUNNERS = {
    "webhook_trigger": pass_through,
    "manual_trigger": pass_through,
    "schedule_trigger": pass_through,
    "validate_json": validate_json,
    "http_request": http_request,
    "transform_data": transform_data,
    "ai_summarizer": summarize,
    "ai_classifier": classify,
    "ai_json_generator": generate_json,
    "conditional_branch": conditional_branch,
    "delay": delay,
    "email_notification": email_notification,
    "slack_notification": slack_notification,
    "report_generator": report_generator,
}
