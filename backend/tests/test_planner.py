from app.engine.planner import ExecutionPlanner
from app.schemas.common import WorkflowGraph


def test_planner_groups_parallel_nodes():
    graph = WorkflowGraph(
        nodes=[
            {"id": "trigger", "type": "manual_trigger", "label": "Manual", "config": {}, "position": {}},
            {"id": "left", "type": "ai_summarizer", "label": "Left", "config": {}, "position": {}},
            {"id": "right", "type": "ai_classifier", "label": "Right", "config": {"categories": ["a"]}, "position": {}},
            {"id": "join", "type": "report_generator", "label": "Report", "config": {}, "position": {}},
        ],
        edges=[
            {"id": "e1", "source": "trigger", "target": "left"},
            {"id": "e2", "source": "trigger", "target": "right"},
            {"id": "e3", "source": "left", "target": "join"},
            {"id": "e4", "source": "right", "target": "join"},
        ],
    )
    plan = ExecutionPlanner().build_plan(graph)
    assert plan["levels"][1] == ["left", "right"]
