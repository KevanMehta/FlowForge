from app.schemas.common import WorkflowGraph
from app.services.graph_validation import GraphValidationService


def test_valid_graph_passes():
    graph = WorkflowGraph(
        nodes=[
            {"id": "a", "type": "manual_trigger", "label": "Manual", "config": {}, "position": {}},
            {"id": "b", "type": "ai_summarizer", "label": "Summarize", "config": {}, "position": {}},
        ],
        edges=[{"id": "e1", "source": "a", "target": "b"}],
    )
    result = GraphValidationService().validate(graph)
    assert result.valid is True


def test_cycle_is_rejected():
    graph = WorkflowGraph(
        nodes=[
            {"id": "a", "type": "manual_trigger", "label": "Manual", "config": {}, "position": {}},
            {"id": "b", "type": "ai_summarizer", "label": "Summarize", "config": {}, "position": {}},
        ],
        edges=[{"id": "e1", "source": "a", "target": "b"}, {"id": "e2", "source": "b", "target": "a"}],
    )
    result = GraphValidationService().validate(graph)
    assert result.valid is False
    assert "cycle" in " ".join(result.errors)
