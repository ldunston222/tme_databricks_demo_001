"""Submission helpers for "episode" payloads.

This module is intentionally service-friendly:
- Accept a plain dict (e.g., JSON-decoded request body)
- Validate/parse into (Episode, actual_outputs) pairs
- Evaluate via EpisodeEvaluator

It can be used from notebooks today and from a future HTTP endpoint later.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

from evaluator.episode import Episode
from evaluator.scoring import EpisodeEvaluator


class InvalidSubmissionPayload(ValueError):
    pass


def parse_submission_payload(payload: Dict[str, Any]) -> List[Tuple[Episode, Dict[str, Any]]]:
    """Parse a submission payload into episode/output pairs.

    Expected payload shape:
    {
      "episodes": [
        {"episode": { ... Episode.to_dict() ... }, "actual_outputs": {...}},
        ...
      ]
    }

    Notes:
    - Invalid items are ignored (to allow partial/best-effort submissions)
    - If no valid items are found, raises InvalidSubmissionPayload
    """
    if not isinstance(payload, dict):
        raise InvalidSubmissionPayload("payload must be a dictionary")

    items = payload.get("episodes")
    if not isinstance(items, list):
        raise InvalidSubmissionPayload("payload['episodes'] must be a list")

    pairs: List[Tuple[Episode, Dict[str, Any]]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        ep_dict = item.get("episode")
        actual = item.get("actual_outputs")

        if not isinstance(ep_dict, dict) or not isinstance(actual, dict):
            continue

        try:
            pairs.append((Episode.from_dict(ep_dict), actual))
        except Exception:
            # Skip malformed episodes
            continue

    if not pairs:
        raise InvalidSubmissionPayload("no valid episodes found in payload")

    return pairs


def evaluate_submission_payload(
    payload: Dict[str, Any],
    *,
    evaluator: EpisodeEvaluator,
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate a submission payload and return the evaluator's batch result."""
    pairs = parse_submission_payload(payload)
    return evaluator.evaluate_batch(pairs, batch_id=batch_id or payload.get("batch_id", "batch_001"))
