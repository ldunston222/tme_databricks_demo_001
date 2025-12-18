# Databricks notebook source
import json
import os
import time
import uuid

from typing import Any


IS_DATABRICKS = bool(os.environ.get('DATABRICKS_RUNTIME_VERSION'))

# Databricks-only global (optional)
try:
    dbutils  # type: ignore[name-defined]
except NameError:
    dbutils = None


def _require_dbutils() -> Any:
    if dbutils is None:
        raise RuntimeError(
            'This notebook must be run in Databricks (dbutils is undefined). '
            'If you want to generate tfvars locally, write a small script instead.'
        )

    return dbutils


def _dbfs_put_json(dbfs_path: str, payload: dict) -> None:
    dbutils_ = _require_dbutils()
    parent = dbfs_path.rsplit('/', 1)[0]
    dbutils_.fs.mkdirs(parent)
    dbutils_.fs.put(dbfs_path, json.dumps(payload, indent=2), overwrite=True)


# COMMAND ----------

# ---- user inputs ----
ENV_NAME = os.getenv('ENV_NAME', 'demo1')
CLOUD = os.getenv('CLOUD', 'aws')  # aws|azure|gcp

# Stable contract for handing inputs to Terraform runners.
TF_RUNS_DBFS_DIR = os.getenv('TF_RUNS_DBFS_DIR', 'dbfs:/FileStore/tme_lab_assembler/terraform_runs')

# Optional override if you want deterministic naming.
TF_RUN_ID = os.getenv('TF_RUN_ID')


# COMMAND ----------

run_id = TF_RUN_ID or (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])

# Contract paths
TFVARS_DBFS_PATH = f"{TF_RUNS_DBFS_DIR.rstrip('/')}/inputs/{run_id}.tfvars.json"

# Minimal tfvars for the MVP Terraform module.
TFVARS = {
    'env_name': ENV_NAME,
    'cloud': CLOUD,
}

print('IS_DATABRICKS:', IS_DATABRICKS)
print('run_id:', run_id)
print('TFVARS_DBFS_PATH:', TFVARS_DBFS_PATH)
print('TFVARS:', json.dumps(TFVARS, indent=2))

_dbfs_put_json(TFVARS_DBFS_PATH, TFVARS)

print('✓ Wrote tfvars to DBFS')
print(TFVARS_DBFS_PATH)
