# AI Workflow Evaluator

A Databricks Spark job for evaluating AI workflow episode idempotency and immutability detection.

## Overview

The AI Workflow Evaluator is designed to evaluate "episodes" - encapsulated units of AI workflow execution - for idempotency and consistency. Each episode represents a complete AI workflow membrane containing:

- **Inputs**: Prompt, configuration, and input data
- **Expected Outputs**: Reference outputs to compare against
- **Metrics**: Token consumption, coherence, drift tracking
- **Accumulated Results**: MLflow-tracked metrics across multiple executions

The system executes episodes as Spark jobs and returns verdicts on whether results maintain idempotency:
- **Match (1.0)**: Actual outputs match expected outputs exactly
- **Mismatch (0.0)**: Outputs diverge significantly
- **Undetermined (0.5)**: Partial or ambiguous results

## Project Structure

```
ai_workflow_evaluator/
├── evaluator/
│   ├── __init__.py          # Package exports
│   ├── episode.py           # Episode class - AI workflow "membrane"
│   ├── metrics.py           # MetricsTracker - MLflow integration
│   ├── scoring.py           # EpisodeEvaluator - idempotency checks
│   └── invariants.py        # Validation rules and assertions
├── datamodel/
│   └── datamodel_db_ddl.sql  # Delta/UC DDL for episodes + evaluations
├── notebooks/
│   ├── demo_evaluator.ipynb             # Demo notebook showing usage
│   ├── setup_datamodel_db.ipynb         # Creates `datamodel_db` schema + tables
│   └── seed_and_browse_datamodel_db.ipynb # Optional: inserts minimal seed data
├── pyproject.toml           # Build configuration, dependencies
└── README.md                # This file
```

## Lakehouse Data Model (Delta/UC)

The repo includes a minimal, versioned “episode lakehouse” schema named `datamodel_db`.

- DDL: `ai_workflow_evaluator/datamodel/datamodel_db_ddl.sql`
- Notebooks: `ai_workflow_evaluator/notebooks/setup_datamodel_db.ipynb` and `ai_workflow_evaluator/notebooks/seed_and_browse_datamodel_db.ipynb`

`episode.status` is constrained to: `successful | degraded | failed`.

## Installation

### Local Development

```bash
cd ai_workflow_evaluator
pip install -e ".[dev]"
```

### On Databricks

On Databricks, `pyspark` is provided by the runtime, so you typically only need to install this project's wheel (and `mlflow` if your runtime doesn't already include it).

Build a wheel locally:

```bash
cd ai_workflow_evaluator
python -m pip install -U build
python -m build
ls -1 dist/*.whl
```

Then install the wheel in Databricks using one of these common options:

- **Cluster Library**: Compute → your cluster → Libraries → Install New → upload the `.whl` from `dist/`.
- **Workspace Files / DBFS**: Upload the `.whl`, then:

```bash
pip install /dbfs/path/to/your-wheel.whl
```

## Quick Start

### Creating an Episode

```python
from evaluator import Episode

episode = Episode(
    inputs={
        "query": "What is the capital of France?",
        "context": "Europe geography"
    },
    expected_outputs={
        "answer": "Paris",
        "confidence": 0.95
    },
    prompt="Answer the geography question based on context",
    model_name="gpt-4",
    token_counts={"input_tokens": 50, "output_tokens": 25}
)
```

### Evaluating an Episode

```python
from evaluator import EpisodeEvaluator

evaluator = EpisodeEvaluator()

# Simulate actual outputs from execution
actual_outputs = {
    "answer": "Paris",
    "confidence": 0.95
}

match_result, metrics = evaluator.evaluate_episode(episode, actual_outputs)
print(f"Match: {match_result}")  # 1.0 = match, 0.0 = mismatch, 0.5 = undetermined
print(f"Drift: {metrics['drift']:.4f}")
print(f"Coherence: {metrics['coherence']:.4f}")
```

### Batch Evaluation (e.g., from a Spark DataFrame)

```python
from pyspark.sql import SparkSession
from evaluator import Episode, EpisodeEvaluator

spark = SparkSession.builder.appName("episode_eval").getOrCreate()

# In practice you might build/derive these pairs from a DataFrame and collect()
episodes_data = [
    (episode1, actual_outputs1),
    (episode2, actual_outputs2),
]

evaluator = EpisodeEvaluator()
results = evaluator.evaluate_batch(episodes_data, batch_id="batch_001")

print(f"Idempotency Rate: {results['summary']['idempotency_rate']:.2%}")
print(f"Average Drift: {results['summary']['avg_drift']:.4f}")
print(f"Average Coherence: {results['summary']['avg_coherence']:.4f}")
```

### Resetting Metrics

```python
# Clear accumulated metrics for an episode
episode.reset_metrics()

# Or get a summary before clearing
summary = episode.get_metrics_summary()
print(summary)
# {
#     'episode_id': 'abc-123',
#     'execution_count': 5,
#     'match_rate': 0.8,
#     'avg_drift': 0.05,
#     'avg_coherence': 0.92,
#     ...
# }
```

### Validating Episodes

```python
from evaluator import validate_episode
from evaluator.invariants import InvalidEpisodeError, assert_idempotent, assert_low_drift

# Validate single episode
try:
    validate_episode(episode)
    print("Episode is valid")
except InvalidEpisodeError as e:
    print(f"Invalid episode: {e}")

# Assert idempotency across episodes
episodes = [episode1, episode2, episode3]
try:
    assert_idempotent(episodes, threshold=0.9)
    print("Episodes are idempotent (≥90%)")
except AssertionError as e:
    print(f"Idempotency assertion failed: {e}")

# Assert low drift
try:
    assert_low_drift(episodes, max_drift=0.1)
    print("Drift is acceptable (≤0.1)")
except AssertionError as e:
    print(f"Drift assertion failed: {e}")
```

## Core Components

### Episode Class

Represents a single AI workflow execution unit with:
- Unique ID (UUID or custom)
- Inputs and expected outputs
- Prompt and model information
- Token consumption tracking
- Accumulated metrics across executions
- Methods: `record_execution()`, `reset_metrics()`, `get_metrics_summary()`, `to_dict()`, `to_json()`

### MetricsTracker

Logs evaluation results to MLflow:
- Manages MLflow runs and experiments
- Logs drift, coherence, idempotency, and token metrics
- Handles batch evaluation summaries
- Integrates with Databricks MLflow tracking

### EpisodeEvaluator

Evaluates episode idempotency:
- Compares actual vs. expected outputs
- Computes drift (output deviation)
- Computes coherence (output consistency)
- Returns match verdicts: 1.0 (match), 0.0 (mismatch), 0.5 (undetermined)
- Supports batch evaluation via `evaluate_batch()`

### Invariants

Validation and assertion framework:
- `validate_episode()`: Enforces required fields and types
- `assert_idempotent()`: Checks proportion of matching executions
- `assert_low_drift()`: Ensures output stability
- `assert_high_coherence()`: Verifies output consistency

## Metrics Tracked

Each episode evaluation logs:

| Metric | Range | Meaning |
|--------|-------|---------|
| `idempotency_score` | [0.0, 1.0] | 1.0 = match, 0.0 = mismatch, 0.5 = undetermined |
| `drift_score` | [0.0, 1.0] | Lower is better; 0.0 = no drift, 1.0 = max deviation |
| `coherence_score` | [0.0, 1.0] | Higher is better; 1.0 = perfectly coherent |
| `input_tokens` | Integer | Token count for inputs |
| `output_tokens` | Integer | Token count for outputs |
| `total_tokens` | Integer | Sum of input + output tokens |

Batch metrics aggregate results across multiple episodes.

## MLflow Integration

All evaluations are automatically logged to MLflow with:
- **Tags**: `episode_id`, `model`, `component`
- **Parameters**: Episode ID, batch ID
- **Metrics**: Drift, coherence, idempotency, tokens
- **Artifacts**: Metadata JSON for each evaluation

Configure MLflow tracking URI:

```python
import mlflow
mlflow.set_tracking_uri("databricks")  # On Databricks
mlflow.set_tracking_uri("http://localhost:5000")  # Local MLflow server
```

## Example: Demo Notebook

See `notebooks/demo_evaluator.ipynb` for a complete working example that:
1. Creates sample episodes
2. Defines mock execution outputs
3. Evaluates episodes for idempotency
4. Displays metrics and summaries
5. Demonstrates batch evaluation
6. Shows metric reset and validation

## Development

### Running Tests

```bash
pytest -v
```

Note: this repo doesn't ship tests yet; add them under `tests/` when ready.

### Code Quality

```bash
black evaluator/
flake8 evaluator/
mypy evaluator/
```

## Future Enhancements

- Spark DataFrame native support (map/filter operations)
- Advanced drift detection (semantic similarity)
- Anomaly detection for outlier episodes
- PySpark UDF wrappers for distributed evaluation
- Configurable idempotency thresholds
- Episode replay and debugging features

## License

MIT

## Contact

TME - Infoblox
