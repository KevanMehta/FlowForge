from app.nodes.registry import classify, summarize


def test_local_ai_summary_is_deterministic():
    out = summarize({"text": "one two three four"}, {}, None, None)
    assert out["summary"] == "one two three four"


def test_classifier_uses_categories():
    out = classify({"text": "billing billing incident"}, {"categories": ["billing", "incident"]}, None, None)
    assert out["category"] == "billing"
