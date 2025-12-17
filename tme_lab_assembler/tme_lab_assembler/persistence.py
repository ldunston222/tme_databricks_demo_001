from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def dbfs_to_local_path(dbfs_path: str) -> str:
    if dbfs_path.startswith("dbfs:/"):
        return "/dbfs/" + dbfs_path[len("dbfs:/") :].lstrip("/")
    return dbfs_path


def dbfs_mkdirs(dbfs_dir: str, *, dbutils: Any | None = None) -> None:
    if dbutils is not None:
        dbutils.fs.mkdirs(dbfs_dir)
        return

    Path(dbfs_to_local_path(dbfs_dir)).mkdir(parents=True, exist_ok=True)


def write_artifact_dbfs(artifact: dict[str, Any], *, dbfs_dir: str, dbutils: Any | None = None) -> str:
    dbfs_mkdirs(dbfs_dir, dbutils=dbutils)

    filename = (
        f"artifact_env={artifact['env_name']}_cloud={artifact['cloud']}_date={artifact['create_at']}.json"
    )
    dbfs_path = dbfs_dir.rstrip("/") + "/" + filename
    payload = json.dumps(artifact, indent=2)

    if dbutils is not None:
        dbutils.fs.put(dbfs_path, payload, overwrite=True)
    else:
        Path(dbfs_to_local_path(dbfs_path)).write_text(payload + "\n", encoding="utf-8")

    return dbfs_path


def ensure_artifact_table(*, spark: Any, table_name: str) -> None:
    db, _tbl = table_name.split(".", 1)
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {db}")
    spark.sql(
        f"""
      CREATE TABLE IF NOT EXISTS {table_name} (
        env_name STRING,
        cloud STRING,
        create_at DATE,
        artifact_path STRING,
        artifact_json STRING
      ) USING DELTA
    """
    )


def write_artifact_table(
    artifact: dict[str, Any],
    *,
    spark: Any,
    table_name: str,
    artifact_path: str | None,
) -> None:
    ensure_artifact_table(spark=spark, table_name=table_name)
    row = {
        "env_name": artifact["env_name"],
        "cloud": artifact["cloud"],
        "create_at": artifact["create_at"],
        "artifact_path": artifact_path,
        "artifact_json": json.dumps(artifact),
    }
    spark.createDataFrame([row]).write.mode("append").saveAsTable(table_name)


def cleanup_artifact(
    *,
    env_name: str,
    dbfs_path: str | None,
    table_name: str | None,
    dbutils: Any | None = None,
    spark: Any | None = None,
) -> None:
    if dbfs_path:
        if dbutils is not None:
            try:
                dbutils.fs.rm(dbfs_path, True)
            except Exception:
                pass
        else:
            try:
                Path(dbfs_to_local_path(dbfs_path)).unlink(missing_ok=True)
            except Exception:
                pass

    if table_name and spark is not None:
        try:
            spark.sql(f"DELETE FROM {table_name} WHERE env_name = '{env_name}'")
        except Exception:
            pass
