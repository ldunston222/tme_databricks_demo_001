"""Episode module - defines the Episode class representing an AI workflow membrane."""

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


class Episode:
    """
    Represents an AI workflow "membrane" - an encapsulated unit of execution
    with inputs, expected outputs, and accumulated metrics.
    
    Attributes:
        episode_id: Unique identifier for the episode
        inputs: Dictionary of input data/prompts
        expected_outputs: Dictionary of expected outputs to compare against
        prompt: The AI prompt used for this episode
        model_name: Name of the AI model used
        token_counts: Dictionary with input_tokens and output_tokens
        metadata: Additional metadata about the episode
        metrics: Accumulated MLflow metrics for this episode
        execution_count: Number of times this episode has been executed
    """
    
    def __init__(
        self,
        inputs: Dict[str, Any],
        expected_outputs: Dict[str, Any],
        prompt: str,
        model_name: str,
        episode_id: Optional[str] = None,
        token_counts: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an Episode."""
        self.episode_id = episode_id or str(uuid.uuid4())
        self.inputs = inputs
        self.expected_outputs = expected_outputs
        self.prompt = prompt
        self.model_name = model_name
        self.token_counts = token_counts or {"input_tokens": 0, "output_tokens": 0}
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()
        
        # Metrics accumulation
        self.metrics: Dict[str, List[float]] = {
            "drift": [],
            "coherence": [],
            "match": [],  # 1.0 for match, 0.0 for mismatch, 0.5 for undetermined
        }
        self.execution_count = 0
        self.last_execution_at: Optional[str] = None
    
    def record_execution(self, match_result: float, drift: float, coherence: float) -> None:
        """
        Record the results of an episode execution.
        
        Args:
            match_result: 1.0 (match), 0.0 (mismatch), 0.5 (undetermined)
            drift: Metric drift score (0.0 to 1.0, lower is better)
            coherence: Coherence score (0.0 to 1.0, higher is better)
        """
        self.metrics["match"].append(match_result)
        self.metrics["drift"].append(drift)
        self.metrics["coherence"].append(coherence)
        self.execution_count += 1
        self.last_execution_at = datetime.utcnow().isoformat()
    
    def reset_metrics(self) -> None:
        """Reset all accumulated metrics and execution count."""
        self.metrics = {
            "drift": [],
            "coherence": [],
            "match": [],
        }
        self.execution_count = 0
        self.last_execution_at = None
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of accumulated metrics."""
        import statistics
        
        summary = {
            "episode_id": self.episode_id,
            "execution_count": self.execution_count,
            "last_execution_at": self.last_execution_at,
        }
        
        if self.metrics["match"]:
            summary["match_rate"] = statistics.mean(self.metrics["match"])
            summary["avg_drift"] = statistics.mean(self.metrics["drift"])
            summary["avg_coherence"] = statistics.mean(self.metrics["coherence"])
            summary["drift_stdev"] = statistics.stdev(self.metrics["drift"]) if len(self.metrics["drift"]) > 1 else 0.0
            summary["coherence_stdev"] = statistics.stdev(self.metrics["coherence"]) if len(self.metrics["coherence"]) > 1 else 0.0
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize episode to dictionary."""
        return {
            "episode_id": self.episode_id,
            "inputs": self.inputs,
            "expected_outputs": self.expected_outputs,
            "prompt": self.prompt,
            "model_name": self.model_name,
            "token_counts": self.token_counts,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "metrics": self.metrics,
            "execution_count": self.execution_count,
            "last_execution_at": self.last_execution_at,
        }
    
    def to_json(self) -> str:
        """Serialize episode to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        """Deserialize episode from dictionary."""
        episode = cls(
            inputs=data["inputs"],
            expected_outputs=data["expected_outputs"],
            prompt=data["prompt"],
            model_name=data["model_name"],
            episode_id=data.get("episode_id"),
            token_counts=data.get("token_counts"),
            metadata=data.get("metadata"),
        )
        # Restore metrics if present
        if "metrics" in data:
            episode.metrics = data["metrics"]
        if "execution_count" in data:
            episode.execution_count = data["execution_count"]
        if "last_execution_at" in data:
            episode.last_execution_at = data["last_execution_at"]
        return episode
    
    def __repr__(self) -> str:
        return f"Episode(id={self.episode_id}, model={self.model_name}, executions={self.execution_count})"
