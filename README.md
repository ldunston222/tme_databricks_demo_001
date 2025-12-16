# tme_databricks_demo_001

This repo contains the **AI Workflow Evaluator** Databricks wheel/job for evaluating episode idempotency (determinism) and logging metrics to MLflow.

## Project

- Main package and docs: `ai_workflow_evaluator/`
- Detailed README: `ai_workflow_evaluator/README.md`
- Notebooks: `ai_workflow_evaluator/notebooks/`

## Quick start

From the repo root:

```bash
cd ai_workflow_evaluator
python -m pip install -U build
python -m build
```

On Databricks, install the wheel and run the Workflows Python wheel entrypoint `ai-workflow-evaluator-job` (details in `ai_workflow_evaluator/README.md`).
