import pytest

from evaluator.episode import Episode
from evaluator.submission import (
    InvalidSubmissionPayload,
    parse_submission_payload,
    evaluate_submission_payload,
)
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


def test_parse_submission_payload_rejects_bad_shapes():
    with pytest.raises(InvalidSubmissionPayload):
        parse_submission_payload([])

    with pytest.raises(InvalidSubmissionPayload):
        parse_submission_payload({"episodes": "nope"})

    with pytest.raises(InvalidSubmissionPayload):
        parse_submission_payload({"episodes": []})


def test_parse_submission_payload_accepts_varied_episode_shapes():
    ep1 = Episode(
        episode_id="ep-nested",
        inputs={"nested": {"a": [1, 2, {"b": "c"}]}, "text": "hello"},
        expected_outputs={"answer": "x", "meta": {"scores": [0.1, 0.2]}},
        prompt="p",
        model_name="m",
    )

    ep2 = Episode(
        episode_id="ep-big",
        inputs={"blob": "x" * 5000, "flags": [True, False, None]},
        expected_outputs={"result": 123, "details": [{"k": "v"}]},
        prompt="p",
        model_name="m",
    )

    payload = {
        "episodes": [
            {"episode": ep1.to_dict(), "actual_outputs": {"answer": "x", "meta": {"scores": [0.1, 0.2]}}},
            {"episode": ep2.to_dict(), "actual_outputs": {"result": 123, "details": [{"k": "v"}]}},
            {"episode": "bad", "actual_outputs": {}},
        ]
    }

    pairs = parse_submission_payload(payload)
    assert len(pairs) == 2
    assert pairs[0][0].episode_id == "ep-nested"
    assert pairs[1][0].episode_id == "ep-big"


def test_evaluate_submission_payload_runs_batch():
    ep = Episode(
        episode_id="ep-1",
        inputs={"a": 1},
        expected_outputs={"x": 1},
        prompt="p",
        model_name="m",
    )

    payload = {"batch_id": "b", "episodes": [{"episode": ep.to_dict(), "actual_outputs": {"x": 1}}]}

    evaluator = EpisodeEvaluator(metrics_tracker=NullMetricsTracker())
    result = evaluate_submission_payload(payload, evaluator=evaluator)

    assert result["batch_id"] == "b"
    assert result["episodes_count"] == 1
    assert result["results"][0]["episode_id"] == "ep-1"
    assert result["results"][0]["match_result"] == 1.0
