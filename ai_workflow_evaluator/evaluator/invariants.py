"""Invariants module - defines validation rules and assertions for episodes."""

from typing import Dict, Any, List, Optional
from evaluator.episode import Episode


class InvalidEpisodeError(Exception):
    """Raised when an episode violates validation invariants."""
    pass


def validate_episode(episode: Episode) -> bool:
    """
    Validate that an episode satisfies all required invariants.
    
    Args:
        episode: The episode to validate
    
    Returns:
        True if episode is valid
    
    Raises:
        InvalidEpisodeError: If episode violates invariants
    """
    _validate_episode_id(episode.episode_id)
    _validate_inputs(episode.inputs)
    _validate_outputs(episode.expected_outputs)
    _validate_prompt(episode.prompt)
    _validate_model_name(episode.model_name)
    _validate_token_counts(episode.token_counts)
    
    return True


def _validate_episode_id(episode_id: str) -> None:
    """Validate episode ID is non-empty string."""
    if not isinstance(episode_id, str) or not episode_id.strip():
        raise InvalidEpisodeError("episode_id must be a non-empty string")


def _validate_inputs(inputs: Dict[str, Any]) -> None:
    """Validate inputs dictionary is properly formatted."""
    if not isinstance(inputs, dict):
        raise InvalidEpisodeError("inputs must be a dictionary")
    
    if len(inputs) == 0:
        raise InvalidEpisodeError("inputs cannot be empty")


def _validate_outputs(outputs: Dict[str, Any]) -> None:
    """Validate expected outputs dictionary is properly formatted."""
    if not isinstance(outputs, dict):
        raise InvalidEpisodeError("expected_outputs must be a dictionary")
    
    if len(outputs) == 0:
        raise InvalidEpisodeError("expected_outputs cannot be empty")


def _validate_prompt(prompt: str) -> None:
    """Validate prompt is non-empty string."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise InvalidEpisodeError("prompt must be a non-empty string")


def _validate_model_name(model_name: str) -> None:
    """Validate model name is non-empty string."""
    if not isinstance(model_name, str) or not model_name.strip():
        raise InvalidEpisodeError("model_name must be a non-empty string")


def _validate_token_counts(token_counts: Dict[str, int]) -> None:
    """Validate token counts are non-negative integers."""
    if not isinstance(token_counts, dict):
        raise InvalidEpisodeError("token_counts must be a dictionary")
    
    if "input_tokens" not in token_counts or "output_tokens" not in token_counts:
        raise InvalidEpisodeError("token_counts must contain 'input_tokens' and 'output_tokens'")
    
    for key, value in token_counts.items():
        if not isinstance(value, int) or value < 0:
            raise InvalidEpisodeError(f"token_counts['{key}'] must be a non-negative integer")


def assert_idempotent(episodes: List[Episode], threshold: float = 0.9) -> bool:
    """
    Assert that episodes demonstrate idempotency above a threshold.
    
    Args:
        episodes: List of episodes to check
        threshold: Minimum proportion of match results required (default 0.9 = 90%)
    
    Returns:
        True if idempotency threshold is met
    
    Raises:
        AssertionError: If threshold not met
    """
    if not episodes:
        raise AssertionError("Cannot assert idempotency on empty episode list")
    
    total_matches = 0
    total_executions = 0
    
    for episode in episodes:
        if episode.metrics["match"]:
            match_count = sum(1 for m in episode.metrics["match"] if m == 1.0)
            total_matches += match_count
            total_executions += len(episode.metrics["match"])
    
    if total_executions == 0:
        raise AssertionError("No executions recorded for episodes")
    
    idempotency_rate = total_matches / total_executions
    
    assert idempotency_rate >= threshold, \
        f"Idempotency rate {idempotency_rate:.2%} below threshold {threshold:.2%}"
    
    return True


def assert_low_drift(episodes: List[Episode], max_drift: float = 0.1) -> bool:
    """
    Assert that episodes have low drift below a threshold.
    
    Args:
        episodes: List of episodes to check
        max_drift: Maximum acceptable average drift (default 0.1)
    
    Returns:
        True if drift is below threshold
    
    Raises:
        AssertionError: If drift exceeds threshold
    """
    if not episodes:
        raise AssertionError("Cannot assert drift on empty episode list")
    
    all_drifts = []
    for episode in episodes:
        all_drifts.extend(episode.metrics["drift"])
    
    if not all_drifts:
        raise AssertionError("No drift metrics recorded for episodes")
    
    import statistics
    avg_drift = statistics.mean(all_drifts)
    
    assert avg_drift <= max_drift, \
        f"Average drift {avg_drift:.4f} exceeds threshold {max_drift:.4f}"
    
    return True


def assert_high_coherence(episodes: List[Episode], min_coherence: float = 0.8) -> bool:
    """
    Assert that episodes maintain high output coherence.
    
    Args:
        episodes: List of episodes to check
        min_coherence: Minimum acceptable average coherence (default 0.8)
    
    Returns:
        True if coherence is above threshold
    
    Raises:
        AssertionError: If coherence is below threshold
    """
    if not episodes:
        raise AssertionError("Cannot assert coherence on empty episode list")
    
    all_coherences = []
    for episode in episodes:
        all_coherences.extend(episode.metrics["coherence"])
    
    if not all_coherences:
        raise AssertionError("No coherence metrics recorded for episodes")
    
    import statistics
    avg_coherence = statistics.mean(all_coherences)
    
    assert avg_coherence >= min_coherence, \
        f"Average coherence {avg_coherence:.4f} below threshold {min_coherence:.4f}"
    
    return True
