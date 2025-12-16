import pytest

from evaluator.episode import Episode
from evaluator.invariants import (
    InvalidEpisodeError,
    validate_episode,
    assert_idempotent,
    assert_low_drift,
    assert_high_coherence,
)


def test_validate_episode_happy_path():
    ep = Episode(
        episode_id="ep",
        inputs={"a": 1},
        expected_outputs={"b": 2},
        prompt="p",
        model_name="m",
        token_counts={"input_tokens": 0, "output_tokens": 0},
    )
    assert validate_episode(ep) is True


def test_validate_episode_rejects_empty_inputs_outputs():
    ep = Episode(inputs={"a": 1}, expected_outputs={"b": 2}, prompt="p", model_name="m")

    ep.inputs = {}
    with pytest.raises(InvalidEpisodeError):
        validate_episode(ep)

    ep.inputs = {"a": 1}
    ep.expected_outputs = {}
    with pytest.raises(InvalidEpisodeError):
        validate_episode(ep)


def test_assertions_require_metrics():
    ep = Episode(inputs={"a": 1}, expected_outputs={"b": 2}, prompt="p", model_name="m")

    with pytest.raises(AssertionError):
        assert_idempotent([ep])

    with pytest.raises(AssertionError):
        assert_low_drift([ep])

    with pytest.raises(AssertionError):
        assert_high_coherence([ep])


def test_assertions_pass_when_metrics_meet_thresholds():
    ep = Episode(inputs={"a": 1}, expected_outputs={"b": 2}, prompt="p", model_name="m")

    # simulate executions
    ep.record_execution(match_result=1.0, drift=0.01, coherence=0.95)
    ep.record_execution(match_result=1.0, drift=0.02, coherence=0.9)

    assert assert_idempotent([ep], threshold=0.9) is True
    assert assert_low_drift([ep], max_drift=0.1) is True
    assert assert_high_coherence([ep], min_coherence=0.8) is True
