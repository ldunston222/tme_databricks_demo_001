# tme_databricks_demo_001

This repo is evolving into a **TME lab assembler**: a reproducible way to build hands-on labs using **GitHub + Databricks notebooks + Terraform + public cloud SDKs**, with a durable **artifact handoff** contract.

`ai_workflow_evaluator/` remains important and will be used later as the “episode engine” to evaluate and operationalize AI-driven workflows that can help generate/validate lab assets (e.g., notebook generation, step scoring, drift checks).

## Components

- `tme_lab_assembler/` (MVP)
	- Atomic unit: a Databricks notebook that runs Terraform, optionally runs cloud SDK steps, and writes an `artifact.json` record to DBFS and/or a Delta table.
	- Notebook: `tme_lab_assembler/notebooks/lab_assembler_mvp.ipynb`
	- Terraform skeleton: `tme_lab_assembler/infra/terraform/mvp/`

- `ai_workflow_evaluator/`
	- Databricks wheel/job to evaluate “episodes” and log metrics to MLflow.
	- Docs: `ai_workflow_evaluator/README.md`
	- Notebooks: `ai_workflow_evaluator/notebooks/`
	- Lakehouse schema: `ai_workflow_evaluator/datamodel/datamodel_db_ddl.sql`

## Quick start

### Lab assembler (Databricks notebook)

- Open `tme_lab_assembler/notebooks/lab_assembler_mvp.ipynb` in Databricks.
- Run cells top-to-bottom. It will:
	- (optionally) trigger cloud SSO login via CLI (AWS/Azure/GCP)
	- run `terraform init` + `terraform apply`
	- write `artifact.json` to DBFS (and optionally a Delta table)
	- provide a `destroy()` helper to tear down infra and cleanup persisted artifacts

### AI workflow evaluator (wheel)

```bash
cd ai_workflow_evaluator
python -m pip install -U build
python -m build
```

On Databricks, install the wheel and run the Workflows Python wheel entrypoint `ai-workflow-evaluator-job` (details in `ai_workflow_evaluator/README.md`).
