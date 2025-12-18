# tme_databricks_demo_001

This repo is evolving into a **TME lab assembler**: a reproducible way to build hands-on labs using **GitHub + Databricks notebooks + Terraform + cloud SDKs**, with a stable **handoff contract** (inputs/outputs/artifacts).

Key subprojects:
- Lab assembler (infra + notebook patterns): `tme_lab_assembler/`
- AI workflow evaluator (episode engine + MLflow metrics): `ai_workflow_evaluator/`

## How to use and build a simple notebook

The current MVP is intentionally simple: a Databricks notebook generates a Terraform `tfvars.json` and stores it to a stable DBFS location.

1) In Databricks, open and run:
- `tme_lab_assembler/notebooks/lab_assembler_tfvars.py`

2) Configure inputs via environment variables (optional):
- `ENV_NAME` (default `demo1`)
- `CLOUD` (default `aws`) — `aws|azure|gcp`
- `TF_RUNS_DBFS_DIR` (default `dbfs:/FileStore/tme_lab_assembler/terraform_runs`)
- `TF_RUN_ID` (optional; otherwise auto-generated)

3) Output contract (what the notebook writes):
- `${TF_RUNS_DBFS_DIR}/inputs/<run_id>.tfvars.json`
- Keys today: `env_name`, `cloud`

If you want to extend the notebook beyond tfvars generation (e.g., consume outputs, write a full artifact record), start from:
- `tme_lab_assembler/notebooks/lab_assembler_mvp.py`

Merge-friendly tip:
- Treat Databricks source notebooks (`# Databricks notebook source` / `# COMMAND ----------`) as the canonical artifact in Git.

## End-to-end workflow (how the system works)

At a high level, notebooks produce inputs, Terraform provisions infrastructure, and outputs are written back to a stable location so downstream steps (including notebooks and lab platforms) can consume them.

```mermaid
flowchart LR
  A[Author notebook in Git] --> B[Run notebook in Databricks]
  B --> C[Write tfvars.json to DBFS]
  C --> D[Terraform runner applies module]
  D --> E[Write outputs/state back to DBFS]
  E --> F[Notebook consumes outputs]
  F --> G[Emit artifact.json handoff]
  G --> H[Lab delivery (e.g., Instruqt) + docs]
  F --> I[Optional: AI workflow evaluator + MLflow]
```

Implementation notes:
- DBFS is used as the “handoff store” for inputs/outputs/state in the MVP.
- Terraform is intended to run outside Databricks (recommended). A runner (e.g., GitHub Actions) reads inputs from DBFS and writes results back.

DBFS contract (defaults shown):
- `TF_RUNS_DBFS_DIR=dbfs:/FileStore/tme_lab_assembler/terraform_runs`
- Inputs: `${TF_RUNS_DBFS_DIR}/inputs/<run_id>.tfvars.json`
- Results (optional): `${TF_RUNS_DBFS_DIR}/results/<run_id>.outputs.json`
- State (optional): `${TF_RUNS_DBFS_DIR}/state/<run_id>/terraform.tfstate`

Runner reference:
- GitHub Actions Terraform runner workflow: `.github/workflows/tme_lab_assembler_terraform.yml`

Where to look:
- Lab assembler docs: `tme_lab_assembler/README.md`
- Terraform MVP module: `tme_lab_assembler/infra/terraform/mvp/`
- Evaluator docs: `ai_workflow_evaluator/README.md`

## Contributing

Two high-value contribution paths:

1) Curate “golden” notebooks
- Add or improve notebooks under `tme_lab_assembler/notebooks/` that demonstrate a clean, reusable pattern (inputs → DBFS contract → outputs/artifact).
- Keep notebooks merge-friendly (prefer Databricks source `.py` over `.ipynb`).
- Document expected environment variables and the exact DBFS paths produced/consumed.

2) Build more Terraform modules and scripts
- Add Terraform modules under `tme_lab_assembler/infra/terraform/<module_name>/`.
- Keep the input contract explicit (what keys you expect in tfvars) and the output contract stable.
- Update the relevant README(s) to describe how the notebook produces inputs for the module.

General contribution guidelines:
- Prefer small, composable changes with clear contracts.
- Avoid committing generated artifacts (e.g., MLflow local tracking directories).

## Vision

Over time, this can grow into a more “product-like” workflow where a simple GUI helps authors generate notebooks/inputs, trigger runners, view outputs, and manage reusable golden assets.
