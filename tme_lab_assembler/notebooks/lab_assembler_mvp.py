# Databricks notebook source
import os

import sys

from datetime import date

from pathlib import Path



# Make the local package importable (Databricks Repos + local dev)

sys.path.insert(0, str(Path('..').resolve()))



from tme_lab_assembler import auth, persistence, terraform



# ---- user inputs ----

ENV_NAME = os.getenv('ENV_NAME', 'demo1')

CLOUD = os.getenv('CLOUD', 'aws')  # aws|azure|gcp



# ---- auth (SSO) ----

# The goal is to establish *interactive* user auth for cloud SDKs.

# In headless environments, prefer device-code / no-browser flows.

AUTH_ENABLED = os.getenv('AUTH_ENABLED', '1') == '0'

AWS_PROFILE = os.getenv('AWS_PROFILE', 'default')

AWS_SSO_START_URL = os.getenv('AWS_SSO_START_URL')

AWS_SSO_REGION = os.getenv('AWS_SSO_REGION')

AWS_SSO_ACCOUNT_ID = os.getenv('AWS_SSO_ACCOUNT_ID')

AWS_SSO_ROLE_NAME = os.getenv('AWS_SSO_ROLE_NAME')

AWS_SSO_NO_BROWSER = os.getenv('AWS_SSO_NO_BROWSER', '1') == '1'

AZ_TENANT_ID = os.getenv('AZ_TENANT_ID')



# Where to persist artifacts:

PERSIST_MODE = os.getenv('PERSIST_MODE', 'dbfs')  # dbfs|table|both

ARTIFACT_DBFS_DIR = os.getenv('ARTIFACT_DBFS_DIR', 'dbfs:/FileStore/tme_lab_assembler/artifacts')

ARTIFACT_TABLE = os.getenv('ARTIFACT_TABLE', 'tme_lab_assembler.artifacts')



# Access placeholders (you can fill these from TF outputs or SDK calls)

ACCESS = {

    'ssh': '...',

    'ui': '...',

    'dns': '...',

}



# Terraform directory relative to this notebook

TF_DIR = str(Path('..') / 'infra' / 'terraform' / 'mvp')



IS_DATABRICKS = bool(os.environ.get('DATABRICKS_RUNTIME_VERSION'))



# Databricks-only globals (optional)

try:

    dbutils  # type: ignore[name-defined]

except NameError:

    dbutils = None



try:

    spark  # type: ignore[name-defined]

except NameError:

    spark = None



print('IS_DATABRICKS:', IS_DATABRICKS)

print('TF_DIR:', Path(TF_DIR).resolve())

# COMMAND ----------

def terraform_init():

    r = terraform.init(TF_DIR)

    print(r.stdout)

    return r



def terraform_apply(env_name: str, cloud: str):

    r = terraform.apply(TF_DIR, env_name=env_name, cloud=cloud)

    print(r.stdout)

    return r



def terraform_destroy(env_name: str, cloud: str):

    r = terraform.destroy(TF_DIR, env_name=env_name, cloud=cloud)

    print(r.stdout)

    return r



def terraform_outputs_json():

    return terraform.output_json(TF_DIR)



print('Helpers ready')

# COMMAND ----------

# Auth (SSO)

auth_info = auth.auth_sso(

    CLOUD,

    enabled=AUTH_ENABLED,

    aws_profile=AWS_PROFILE,

    aws_sso_start_url=AWS_SSO_START_URL,

    aws_sso_region=AWS_SSO_REGION,

    aws_sso_account_id=AWS_SSO_ACCOUNT_ID,

    aws_sso_role_name=AWS_SSO_ROLE_NAME,

    aws_sso_no_browser=AWS_SSO_NO_BROWSER,

    az_tenant_id=AZ_TENANT_ID,

)

auth_info

# COMMAND ----------

# Provision

terraform_init()

terraform_apply(ENV_NAME, CLOUD)

tf_outputs = terraform_outputs_json()

print('Terraform outputs keys:', list(tf_outputs.keys()))

# COMMAND ----------

# Build artifact (first handoff record)

artifact = {

    'env_name': ENV_NAME,

    'cloud': CLOUD,

    'auth': auth_info,

    'resources': tf_outputs,

    'access': ACCESS,

    'create_at': date.today().isoformat(),

}

artifact

# COMMAND ----------

# Persist artifact to DBFS and/or Delta table

artifact_dbfs_path = None



if PERSIST_MODE in ('dbfs', 'both'):

    artifact_dbfs_path = persistence.write_artifact_dbfs(

        artifact,

        dbfs_dir=ARTIFACT_DBFS_DIR,

        dbutils=dbutils,

    )

    print('Wrote artifact to:', artifact_dbfs_path)



if PERSIST_MODE in ('table', 'both'):

    if not IS_DATABRICKS:

        raise RuntimeError('Delta table persistence requires Spark (Databricks).')

    if spark is None:

        raise RuntimeError('Spark session not available (spark is undefined).')

    persistence.write_artifact_table(

        artifact,

        spark=spark,

        table_name=ARTIFACT_TABLE,

        artifact_path=artifact_dbfs_path,

    )

    print('Appended artifact row to:', ARTIFACT_TABLE)



artifact_dbfs_path

# COMMAND ----------

# Cleanup / destroy

# - destroys infra via Terraform

# - removes the DBFS artifact file and/or deletes Delta rows for env_name



def destroy(env_name: str = ENV_NAME, cloud: str = CLOUD, *, dbfs_path: str | None = artifact_dbfs_path):

    terraform_destroy(env_name, cloud)

    persistence.cleanup_artifact(

        env_name=env_name,

        dbfs_path=dbfs_path,

        table_name=(ARTIFACT_TABLE if PERSIST_MODE in ('table', 'both') else None),

        dbutils=dbutils,

        spark=spark,

    )

    print('✓ Destroy complete')



print('Call destroy() when ready')
