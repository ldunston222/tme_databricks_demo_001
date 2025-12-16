import json

import pytest

from evaluator.episode import Episode


def test_episode_has_default_id_and_serializes_roundtrip():
    ep = Episode(
        inputs={"a": 1},
        expected_outputs={"out": "x"},
        prompt="p",
        model_name="m",
        token_counts={"input_tokens": 1, "output_tokens": 2},
        metadata={"nested": {"k": [1, 2, 3]}},
    )

    assert isinstance(ep.episode_id, str) and ep.episode_id

    d = ep.to_dict()
    ep2 = Episode.from_dict(d)

    assert ep2.episode_id == ep.episode_id
    assert ep2.inputs == ep.inputs
    assert ep2.expected_outputs == ep.expected_outputs
    assert ep2.prompt == ep.prompt
    assert ep2.model_name == ep.model_name
    assert ep2.token_counts == ep.token_counts
    assert ep2.metadata == ep.metadata

    # JSON should be valid
    parsed = json.loads(ep.to_json())
    assert parsed["episode_id"] == ep.episode_id


def test_episode_records_and_resets_metrics():
    ep = Episode(inputs={"q": "x"}, expected_outputs={"a": "y"}, prompt="p", model_name="m")

    assert ep.execution_count == 0
    assert ep.get_metrics_summary()["execution_count"] == 0

    ep.record_execution(match_result=1.0, drift=0.0, coherence=1.0)
    ep.record_execution(match_result=0.5, drift=0.2, coherence=0.8)

    summary = ep.get_metrics_summary()
    assert summary["execution_count"] == 2
    assert 0.0 <= summary["avg_drift"] <= 1.0
    assert 0.0 <= summary["avg_coherence"] <= 1.0
    assert 0.0 <= summary["match_rate"] <= 1.0

    ep.reset_metrics()
    assert ep.execution_count == 0
    assert ep.metrics["match"] == []
    assert ep.metrics["drift"] == []
    assert ep.metrics["coherence"] == []


def test_episode_token_counts_default_shape():
    ep = Episode(inputs={"q": 1}, expected_outputs={"a": 2}, prompt="p", model_name="m")
    assert ep.token_counts["input_tokens"] == 0
    assert ep.token_counts["output_tokens"] == 0
