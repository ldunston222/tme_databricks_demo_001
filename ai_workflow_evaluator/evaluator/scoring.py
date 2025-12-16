"""Scoring module - implements episode evaluation and idempotency checking."""

from typing import Dict, Any, Tuple, Optional, List
import json
import statistics
from evaluator.episode import Episode
from evaluator.metrics import MetricsTracker


class EpisodeEvaluator:
    """
    Evaluates episodes for idempotency by comparing expected outputs
    against actual execution results.
    """
    
    def __init__(self, metrics_tracker: Optional[MetricsTracker] = None):
        """
        Initialize EpisodeEvaluator.
        
        Args:
            metrics_tracker: Optional MetricsTracker instance. Creates new one if not provided.
        """
        self.metrics_tracker = metrics_tracker or MetricsTracker()
    
    def evaluate_episode(self, episode: Episode, actual_outputs: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """
        Evaluate a single episode by comparing actual outputs against expected.
        
        Args:
            episode: The episode to evaluate
            actual_outputs: The actual outputs from execution
        
        Returns:
            Tuple of (match_result, metrics_dict) where:
            - match_result: 1.0 (match), 0.0 (mismatch), 0.5 (undetermined)
            - metrics_dict: Contains drift and coherence scores
        """
        # Compute match result
        match_result = self._compute_match(episode.expected_outputs, actual_outputs)
        
        # Compute drift (difference between outputs)
        drift = self._compute_drift(episode.expected_outputs, actual_outputs)
        
        # Compute coherence (internal consistency of outputs)
        coherence = self._compute_coherence(actual_outputs)
        
        # Record execution in episode
        episode.record_execution(match_result, drift, coherence)
        
        # Log to MLflow
        run_id = self.metrics_tracker.start_run(
            episode.episode_id,
            tags={"model": episode.model_name}
        )
        self.metrics_tracker.log_evaluation_result(
            episode_id=episode.episode_id,
            match_result=match_result,
            drift=drift,
            coherence=coherence,
            token_counts=episode.token_counts,
            metadata={
                "inputs_hash": hash(json.dumps(episode.inputs, sort_keys=True, default=str)),
                "expected_outputs_hash": hash(json.dumps(episode.expected_outputs, sort_keys=True, default=str)),
                "actual_outputs_hash": hash(json.dumps(actual_outputs, sort_keys=True, default=str)),
            }
        )
        self.metrics_tracker.end_run()
        
        return match_result, {
            "drift": drift,
            "coherence": coherence,
            "match_result": match_result,
        }
    
    def evaluate_batch(self, episodes_with_outputs: List[Tuple[Episode, Dict[str, Any]]], batch_id: str = "batch_001") -> Dict[str, Any]:
        """
        Evaluate a batch of episodes (typically from a Spark DataFrame).
        
        Args:
            episodes_with_outputs: List of (Episode, actual_outputs) tuples
            batch_id: Identifier for the batch
        
        Returns:
            Batch evaluation summary with aggregate metrics
        """
        if not episodes_with_outputs:
            return {
                "batch_id": batch_id,
                "episodes_count": 0,
                "results": [],
            }
        
        batch_results = []
        match_results = []
        drifts = []
        coherences = []
        total_tokens = 0
        
        for episode, actual_outputs in episodes_with_outputs:
            match_result, metrics = self.evaluate_episode(episode, actual_outputs)
            
            batch_results.append({
                "episode_id": episode.episode_id,
                "match_result": match_result,
                "metrics": metrics,
            })
            
            match_results.append(match_result)
            drifts.append(metrics["drift"])
            coherences.append(metrics["coherence"])
            total_tokens += episode.token_counts.get("input_tokens", 0) + episode.token_counts.get("output_tokens", 0)
        
        # Compute batch aggregates
        avg_drift = statistics.mean(drifts)
        avg_coherence = statistics.mean(coherences)
        idempotency_rate = sum(1 for r in match_results if r == 1.0) / len(match_results)
        
        # Log batch results
        self.metrics_tracker.log_batch_evaluation(
            batch_id=batch_id,
            episodes_count=len(episodes_with_outputs),
            avg_drift=avg_drift,
            avg_coherence=avg_coherence,
            idempotency_rate=idempotency_rate,
            total_tokens=total_tokens,
        )
        
        return {
            "batch_id": batch_id,
            "episodes_count": len(episodes_with_outputs),
            "results": batch_results,
            "summary": {
                "avg_drift": avg_drift,
                "avg_coherence": avg_coherence,
                "idempotency_rate": idempotency_rate,
                "total_tokens": total_tokens,
                "drift_stdev": statistics.stdev(drifts) if len(drifts) > 1 else 0.0,
                "coherence_stdev": statistics.stdev(coherences) if len(coherences) > 1 else 0.0,
            }
        }
    
    def _compute_match(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> float:
        """
        Compute if outputs match exactly.
        
        Returns: 1.0 (match), 0.0 (mismatch), 0.5 (undetermined/partial)
        """
        if not expected or not actual:
            return 0.5  # Undetermined
        
        if expected == actual:
            return 1.0  # Perfect match
        
        # Check partial match (if any key-value pairs match)
        matching_keys = sum(1 for k in expected if k in actual and expected[k] == actual[k])
        total_keys = max(len(expected), len(actual))
        
        if matching_keys == 0:
            return 0.0  # No match
        elif matching_keys == total_keys:
            return 1.0  # All match
        else:
            return 0.5  # Partial match
    
    def _compute_drift(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> float:
        """
        Compute metric drift (difference magnitude between outputs).
        
        Returns: Float between 0.0 (no drift) and 1.0 (maximum drift)
        """
        if not expected:
            return 0.5  # Undetermined
        
        # Numeric drift detection
        numeric_diffs = []
        
        for key, expected_val in expected.items():
            if key not in actual:
                numeric_diffs.append(1.0)  # Missing key = max drift
                continue
            
            actual_val = actual[key]
            
            # Try numeric comparison
            try:
                if isinstance(expected_val, (int, float)) and isinstance(actual_val, (int, float)):
                    if expected_val == 0:
                        drift = 1.0 if actual_val != 0 else 0.0
                    else:
                        drift = abs(actual_val - expected_val) / abs(expected_val)
                        drift = min(1.0, drift)  # Cap at 1.0
                    numeric_diffs.append(drift)
                elif expected_val == actual_val:
                    numeric_diffs.append(0.0)
                else:
                    numeric_diffs.append(1.0)  # Different values = max drift
            except (TypeError, ZeroDivisionError):
                numeric_diffs.append(1.0 if expected_val != actual_val else 0.0)
        
        return statistics.mean(numeric_diffs) if numeric_diffs else 0.5
    
    def _compute_coherence(self, outputs: Dict[str, Any]) -> float:
        """
        Compute output coherence (internal consistency).
        
        Returns: Float between 0.0 (incoherent) and 1.0 (perfectly coherent)
        """
        if not outputs:
            return 0.5
        
        # Simple heuristic: check if output values are non-null and of consistent types
        values = list(outputs.values())
        
        if not values:
            return 0.5
        
        # All non-null
        non_null_count = sum(1 for v in values if v is not None)
        null_ratio = 1.0 - (non_null_count / len(values))
        
        # Type consistency
        types = [type(v).__name__ for v in values if v is not None]
        if types:
            most_common_type = max(set(types), key=types.count)
            type_consistency = types.count(most_common_type) / len(types)
        else:
            type_consistency = 0.0
        
        # Coherence = (null_ratio penalty) + type_consistency
        coherence = (1.0 - null_ratio) * 0.5 + type_consistency * 0.5
        
        return min(1.0, max(0.0, coherence))
