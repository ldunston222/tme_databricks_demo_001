"""Metrics module - defines metrics tracking for episodes."""

from typing import Dict, Any, Optional
import json
import mlflow
import mlflow.entities
from datetime import datetime


class MetricsTracker:
    """
    Tracks and logs MLflow metrics for episode evaluations.
    Handles drift detection, coherence scoring, and idempotency tracking.
    """
    
    def __init__(self, experiment_name: str = "episode_evaluation"):
        """
        Initialize MetricsTracker.
        
        Args:
            experiment_name: MLflow experiment name for tracking runs
        """
        self.experiment_name = experiment_name
        mlflow.set_experiment(experiment_name)
    
    def start_run(self, episode_id: str, tags: Optional[Dict[str, str]] = None, nested: bool = True) -> str:
        """
        Start a new MLflow run for episode evaluation.
        
        Args:
            episode_id: The episode being evaluated
            tags: Additional tags to attach to the run
            nested: Whether to use nested runs (default True for sequential evaluations)
        
        Returns:
            The run ID
        """
        default_tags = {
            "episode_id": episode_id,
            "component": "evaluator",
        }
        if tags:
            default_tags.update(tags)
        
        # Use nested=True by default for sequential episode evaluations
        # This prevents "run already active" errors when evaluating multiple episodes
        run = mlflow.start_run(nested=nested)
        mlflow.set_tags(default_tags)
        
        return run.info.run_id
    
    def end_run(self) -> None:
        """End the current MLflow run (or nested run context)."""
        try:
            mlflow.end_run()
        except Exception:
            # Nested runs may auto-close; ignore errors
            pass
    
    def log_drift_metric(self, drift_score: float, step: Optional[int] = None) -> None:
        """
        Log drift metric indicating deviation between expected and actual outputs.
        
        Args:
            drift_score: Float between 0.0 (no drift) and 1.0 (maximum drift)
            step: Optional step/iteration number
        """
        mlflow.log_metric("drift_score", drift_score, step=step)
    
    def log_coherence_metric(self, coherence_score: float, step: Optional[int] = None) -> None:
        """
        Log coherence metric indicating consistency of outputs.
        
        Args:
            coherence_score: Float between 0.0 (incoherent) and 1.0 (perfectly coherent)
            step: Optional step/iteration number
        """
        mlflow.log_metric("coherence_score", coherence_score, step=step)
    
    def log_idempotency_metric(self, is_idempotent: float, step: Optional[int] = None) -> None:
        """
        Log idempotency metric (0.0 = not idempotent, 1.0 = idempotent, 0.5 = undetermined).
        
        Args:
            is_idempotent: Binary or ternary score
            step: Optional step/iteration number
        """
        mlflow.log_metric("idempotency_score", is_idempotent, step=step)
    
    def log_token_usage(self, input_tokens: int, output_tokens: int, step: Optional[int] = None) -> None:
        """
        Log token usage metrics.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            step: Optional step/iteration number
        """
        mlflow.log_metric("input_tokens", input_tokens, step=step)
        mlflow.log_metric("output_tokens", output_tokens, step=step)
        mlflow.log_metric("total_tokens", input_tokens + output_tokens, step=step)
    
    def log_evaluation_result(
        self,
        episode_id: str,
        match_result: float,
        drift: float,
        coherence: float,
        token_counts: Dict[str, int],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log complete evaluation result for an episode.
        
        Args:
            episode_id: The episode ID
            match_result: 1.0 (match), 0.0 (mismatch), 0.5 (undetermined)
            drift: Drift score (0.0 to 1.0)
            coherence: Coherence score (0.0 to 1.0)
            token_counts: Dictionary with input/output token counts
            metadata: Additional metadata to log
        """
        # Log metrics
        self.log_idempotency_metric(match_result)
        self.log_drift_metric(drift)
        self.log_coherence_metric(coherence)
        self.log_token_usage(
            token_counts.get("input_tokens", 0),
            token_counts.get("output_tokens", 0),
        )
        
        # Log parameters
        mlflow.log_param("episode_id", episode_id)
        
        # Log metadata as artifact if provided
        if metadata:
            mlflow.log_dict(metadata, "evaluation_metadata.json")
    
    def log_batch_evaluation(
        self,
        batch_id: str,
        episodes_count: int,
        avg_drift: float,
        avg_coherence: float,
        idempotency_rate: float,
        total_tokens: int,
    ) -> None:
        """
        Log results from batch evaluation of multiple episodes.
        
        Args:
            batch_id: Identifier for the batch
            episodes_count: Number of episodes in batch
            avg_drift: Average drift across batch
            avg_coherence: Average coherence across batch
            idempotency_rate: Proportion of idempotent episodes
            total_tokens: Total tokens consumed by batch
        """
        mlflow.log_param("batch_id", batch_id)
        mlflow.log_param("batch_size", episodes_count)
        mlflow.log_metric("batch_avg_drift", avg_drift)
        mlflow.log_metric("batch_avg_coherence", avg_coherence)
        mlflow.log_metric("batch_idempotency_rate", idempotency_rate)
        mlflow.log_metric("batch_total_tokens", total_tokens)
