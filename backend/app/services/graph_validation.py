from collections import defaultdict, deque
from ..models.enums import NodeType
from ..schemas.common import WorkflowGraph, ValidationResult


TRIGGER_TYPES = {NodeType.webhook_trigger, NodeType.manual_trigger, NodeType.schedule_trigger}
REQUIRED_CONFIG = {
    NodeType.validate_json: ["schema"],
    NodeType.http_request: ["method", "url"],
    NodeType.ai_classifier: ["categories"],
    NodeType.delay: ["seconds"],
    NodeType.email_notification: ["recipient"],
    NodeType.slack_notification: ["channel"],
}


class GraphValidationService:
    def validate(self, graph: WorkflowGraph) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        node_ids = [node.id for node in graph.nodes]
        node_set = set(node_ids)
        if len(node_ids) != len(node_set):
            errors.append("Node IDs must be unique.")
        if not graph.nodes:
            errors.append("Workflow must contain at least one node.")

        trigger_count = 0
        for node in graph.nodes:
            try:
                node_type = NodeType(node.type)
            except ValueError:
                errors.append(f"Node {node.id} has unsupported type {node.type}.")
                continue
            if node_type in TRIGGER_TYPES:
                trigger_count += 1
            for key in REQUIRED_CONFIG.get(node_type, []):
                if key not in node.config:
                    errors.append(f"Node {node.label} is missing required config: {key}.")
        if trigger_count == 0:
            errors.append("Workflow must include a trigger node.")

        adjacency: dict[str, list[str]] = defaultdict(list)
        indegree = {node_id: 0 for node_id in node_ids}
        for edge in graph.edges:
            if edge.source not in node_set:
                errors.append(f"Edge {edge.id} references missing source {edge.source}.")
            if edge.target not in node_set:
                errors.append(f"Edge {edge.id} references missing target {edge.target}.")
            if edge.source == edge.target:
                errors.append(f"Edge {edge.id} cannot connect a node to itself.")
            if edge.source in node_set and edge.target in node_set:
                adjacency[edge.source].append(edge.target)
                indegree[edge.target] += 1

        visited = []
        queue = deque([node_id for node_id, degree in indegree.items() if degree == 0])
        while queue:
            node_id = queue.popleft()
            visited.append(node_id)
            for child in adjacency[node_id]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if len(visited) != len(node_ids):
            errors.append("Workflow graph contains a cycle.")

        connected = set()
        for edge in graph.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        disconnected = node_set - connected
        trigger_only = {n.id for n in graph.nodes if n.type in {t.value for t in TRIGGER_TYPES}}
        disconnected = disconnected - trigger_only if len(graph.nodes) == 1 else disconnected
        if disconnected:
            errors.append(f"Workflow contains disconnected nodes: {', '.join(sorted(disconnected))}.")

        if not errors and len(graph.nodes) > 20:
            warnings.append("Large workflows may need additional worker capacity.")
        return ValidationResult(valid=not errors, errors=errors, warnings=warnings)
