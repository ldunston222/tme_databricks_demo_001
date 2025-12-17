# TME Lab Assembler (MVP)

MVP goal: one Databricks notebook that provisions infra with Terraform, establishes interactive cloud auth (SSO) for SDK usage, and persists a single `artifact.json` handoff record to **DBFS** or a **Delta table**.

## Key paths
- Notebook (Databricks source, merge-friendly): `tme_lab_assembler/notebooks/lab_assembler_mvp.py`
- (Optional) Notebook JSON (VS Code preview only): `tme_lab_assembler/notebooks/lab_assembler_mvp_local.ipynb`
- Terraform module: `tme_lab_assembler/infra/terraform/mvp/`

## Artifact shape
The notebook emits an `artifact` dict like:

```json
{
  "env_name": "demo1",
  "cloud": "aws",
  "auth": {"provider": "aws", "method": "aws-cli sso login", "status": "ok", "profile": "default"},
  "resources": {"...": "terraform output -json"},
  "access": {"ssh": "...", "ui": "...", "dns": "..."},
  "create_at": "2025-xx-xx"
}
```

Notes:
- The `auth` section is *metadata only* (no secrets are stored in the artifact).
- `resources` is the raw `terraform output -json` payload.

## Notebook inputs

The notebook reads these environment variables (with defaults):
- `ENV_NAME` (default `demo1`)
- `CLOUD` (default `aws`) — `aws|azure|gcp`
- `AUTH_ENABLED` (default `1`) — set to `0` to skip interactive auth
- AWS SSO (optional): `AWS_PROFILE`, `AWS_SSO_START_URL`, `AWS_SSO_REGION`, `AWS_SSO_ACCOUNT_ID`, `AWS_SSO_ROLE_NAME`, `AWS_SSO_NO_BROWSER`
- Azure (optional): `AZ_TENANT_ID`
- Persistence: `PERSIST_MODE` (`dbfs|table|both`), `ARTIFACT_DBFS_DIR`, `ARTIFACT_TABLE`

## Notes
- The notebook assumes a `terraform` binary is available on the cluster driver.
- Cloud SSO uses provider CLIs (`aws`, `az`, `gcloud`) if present; in headless runtimes, device-code/no-browser flows are preferred.
- Persistence defaults to DBFS (e.g. `dbfs:/FileStore/tme_lab_assembler/artifacts`). Delta-table persistence is optional (`tme_lab_assembler.artifacts`).
- Cleanup: call `destroy()` in the notebook to run `terraform destroy` and remove persisted artifact(s).

## Merge-friendly workflow (recommended)
- Treat `tme_lab_assembler/notebooks/lab_assembler_mvp.py` as the source of truth for Databricks.
- Avoid editing/merging `.ipynb` for Databricks Repos: JSON cell IDs churn and cause frequent conflicts.
- Keep substantial logic in importable modules under `tme_lab_assembler/tme_lab_assembler/` and keep the notebook as an orchestrator.

If you ever need to regenerate the Databricks source notebook from the `.ipynb`:
- `python tme_lab_assembler/tools/ipynb_to_databricks_py.py tme_lab_assembler/notebooks/lab_assembler_mvp_local.ipynb`
