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
CLOUD = os.getenv('CLOUD', 'azure')  # aws|azure|gcp

# Stable contract for handing inputs to Terraform runners.
TF_RUNS_DBFS_DIR = os.getenv('TF_RUNS_DBFS_DIR', 'dbfs:/FileStore/tme_lab_assembler/terraform_runs')

# Optional override if you want deterministic naming.
TF_RUN_ID = os.getenv('TF_RUN_ID')

# Azure MVP module inputs
AZ_LOCATION = os.getenv('AZ_LOCATION', 'eastus')
AZ_ADMIN_USERNAME = os.getenv('AZ_ADMIN_USERNAME', 'azureuser')
AZ_SSH_PUBLIC_KEY = os.getenv('AZ_SSH_PUBLIC_KEY')
AZ_VM_SIZE = os.getenv('AZ_VM_SIZE', 'Standard_B1s')
AZ_DNS_ZONE_NAME = os.getenv('AZ_DNS_ZONE_NAME', 'joespizza.com')
AZ_CREATE_DNS_ZONE = os.getenv('AZ_CREATE_DNS_ZONE', '1') == '1'


# COMMAND ----------

run_id = TF_RUN_ID or (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])

# Contract paths
TFVARS_DBFS_PATH = f"{TF_RUNS_DBFS_DIR.rstrip('/')}/inputs/{run_id}.tfvars.json"

# Minimal tfvars for the MVP Terraform module.
TFVARS = {
    'env_name': ENV_NAME,
    'cloud': CLOUD,
}

if CLOUD == 'azure':
    if not AZ_SSH_PUBLIC_KEY:
        raise RuntimeError(
            'CLOUD=azure requires AZ_SSH_PUBLIC_KEY (OpenSSH public key string). '
            'Example: ssh-ed25519 AAAA... user@host'
        )

    TFVARS.update(
        {
            'location': AZ_LOCATION,
            'admin_username': AZ_ADMIN_USERNAME,
            'ssh_public_key': AZ_SSH_PUBLIC_KEY,
            'vm_size': AZ_VM_SIZE,
            'dns_zone_name': AZ_DNS_ZONE_NAME,
            'create_dns_zone': AZ_CREATE_DNS_ZONE,
        }
    )

print('IS_DATABRICKS:', IS_DATABRICKS)
print('run_id:', run_id)
print('TFVARS_DBFS_PATH:', TFVARS_DBFS_PATH)
print('TFVARS:', json.dumps(TFVARS, indent=2))

_dbfs_put_json(TFVARS_DBFS_PATH, TFVARS)

print('✓ Wrote tfvars to DBFS')
print(TFVARS_DBFS_PATH)
