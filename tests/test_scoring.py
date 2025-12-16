import pytest

from evaluator.episode import Episode
from evaluator.scoring import EpisodeEvaluator


class NullMetricsTracker:
    def start_run(self, episode_id: str, tags=None, nested: bool = True):
        return "test-run"

    def log_evaluation_result(self, **kwargs):
        return None

    def log_batch_evaluation(self, **kwargs):
        return None

    def end_run(self):
        return None


def make_evaluator() -> EpisodeEvaluator:
    return EpisodeEvaluator(metrics_tracker=NullMetricsTracker())


def test_compute_match_exact_mismatch_partial():
    ev = make_evaluator()

    assert ev._compute_match({"a": 1}, {"a": 1}) == 1.0
    assert ev._compute_match({"a": 1}, {"a": 2}) == 0.0
    assert ev._compute_match({"a": 1, "b": 2}, {"a": 1, "b": 3}) == 0.5

    # Undetermined when expected or actual is empty
    assert ev._compute_match({}, {"a": 1}) == 0.5
    assert ev._compute_match({"a": 1}, {}) == 0.5


def test_compute_drift_numeric_and_missing_keys():
    ev = make_evaluator()

    assert ev._compute_drift({"x": 10}, {"x": 10}) == 0.0

    # 20 vs 10 => 100% drift capped at 1.0
    assert ev._compute_drift({"x": 10}, {"x": 20}) == 1.0

    # Missing key => max drift
    assert ev._compute_drift({"x": 1, "y": 2}, {"x": 1}) == pytest.approx(0.5)


def test_compute_coherence_nulls_and_types():
    ev = make_evaluator()

    assert ev._compute_coherence({}) == 0.5
    assert ev._compute_coherence({"a": None, "b": None}) == 0.0

    # All present, consistent types
    c1 = ev._compute_coherence({"a": 1, "b": 2, "c": 3})
    assert 0.8 <= c1 <= 1.0

    # Mixed types reduces score
    c2 = ev._compute_coherence({"a": 1, "b": "x", "c": [1, 2]})
    assert 0.0 <= c2 <= 1.0
    assert c2 < c1


def test_evaluate_episode_records_metrics_and_returns_dict():
    ev = make_evaluator()

    ep = Episode(
        episode_id="ep-1",
        inputs={"nested": {"a": [1, 2, {"b": "c"}]}, "text": "hello"},
        expected_outputs={"answer": "Paris", "confidence": 0.95},
        prompt="p",
        model_name="m",
        token_counts={"input_tokens": 12, "output_tokens": 3},
    )

    match, metrics = ev.evaluate_episode(ep, {"answer": "Paris", "confidence": 0.95})
    assert match == 1.0
    assert metrics["match_result"] == 1.0
    assert "drift" in metrics and "coherence" in metrics
    assert ep.execution_count == 1


def test_evaluate_batch_returns_summary_even_with_one_bad_episode():
    ev = make_evaluator()

    ep1 = Episode(inputs={"q": "a"}, expected_outputs={"x": 1}, prompt="p", model_name="m")
    ep2 = Episode(inputs={"q": "b"}, expected_outputs={"x": 2}, prompt="p", model_name="m")

    # Make one episode "bad" by passing a non-dict actual_outputs which triggers exception
    results = ev.evaluate_batch([(ep1, {"x": 1}), (ep2, None)], batch_id="b")

    assert results["batch_id"] == "b"
    assert results["episodes_count"] == 2
    assert "results" in results
    assert "summary" in results
