from collections import defaultdict, deque
from ..schemas.common import WorkflowGraph


class ExecutionPlanner:
    def build_plan(self, graph: WorkflowGraph) -> dict:
        adjacency: dict[str, list[str]] = defaultdict(list)
        indegree = {node.id: 0 for node in graph.nodes}
        node_lookup = {node.id: node.model_dump() for node in graph.nodes}
        for edge in graph.edges:
            adjacency[edge.source].append(edge.target)
            indegree[edge.target] += 1

        ready = deque([node_id for node_id, degree in indegree.items() if degree == 0])
        levels: list[list[str]] = []
        while ready:
            group = list(ready)
            ready.clear()
            levels.append(group)
            for node_id in group:
                for child in adjacency[node_id]:
                    indegree[child] -= 1
                    if indegree[child] == 0:
                        ready.append(child)
        return {"levels": levels, "nodes": node_lookup, "edges": [edge.model_dump() for edge in graph.edges]}
