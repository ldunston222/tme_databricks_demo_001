-- datamodel_db: minimal Delta/UC schema for immutable episodes + evaluations
--
-- Usage (Databricks SQL):
--   %sql
--   -- paste this file
--
-- Usage (PySpark):
--   for stmt in open("datamodel_db_ddl.sql").read().split(";\n"):
--       if stmt.strip(): spark.sql(stmt)

CREATE SCHEMA IF NOT EXISTS datamodel_db;

-- Episode header (immutable logical unit; versioned)
CREATE TABLE IF NOT EXISTS datamodel_db.episode (
  episode_id STRING NOT NULL,
  episode_version INT NOT NULL,
  created_at TIMESTAMP,
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  duration_ms BIGINT,

  status STRING NOT NULL,

  workflow_name STRING,
  model_name STRING,
  model_version STRING,
  agent_version STRING,

  is_golden BOOLEAN,
  golden_template_id STRING,

  -- Optional provenance
  source STRING,
  source_ref STRING,

  -- Payloads stored as JSON strings to keep schema stable
  inputs_json STRING,
  expected_outputs_json STRING,
  actual_outputs_json STRING,
  metadata_json STRING,

  -- Optional costs (populate from your runtime pricing model)
  cost_usd DOUBLE,
  cost_input_usd DOUBLE,
  cost_output_usd DOUBLE,

  -- Optional token counts
  input_tokens BIGINT,
  output_tokens BIGINT,
  total_tokens BIGINT,

  CONSTRAINT episode_status_check CHECK (status IN ('successful', 'degraded', 'failed'))
)
USING DELTA;

-- Step-level trace for an episode (ordered by step_index)
CREATE TABLE IF NOT EXISTS datamodel_db.episode_steps (
  episode_id STRING NOT NULL,
  episode_version INT NOT NULL,
  step_index INT NOT NULL,

  -- E.g. "system"|"user"|"assistant"|"tool" or any workflow-specific step type
  step_type STRING,
  step_name STRING,
  content STRING,
  created_at TIMESTAMP,

  -- Optional per-step metrics
  tokens_in BIGINT,
  tokens_out BIGINT,
  total_tokens BIGINT,
  latency_ms BIGINT,
  score DOUBLE,

  -- Optional failure annotation
  failure_type STRING,
  invariant_violated STRING,

  metadata_json STRING,

  CONSTRAINT step_index_nonnegative CHECK (step_index >= 0)
)
USING DELTA;

-- Evaluation results for an episode (can be multiple runs per episode/version)
CREATE TABLE IF NOT EXISTS datamodel_db.episode_evaluation (
  evaluation_id STRING NOT NULL,
  episode_id STRING NOT NULL,
  episode_version INT NOT NULL,
  evaluated_at TIMESTAMP,

  evaluator_name STRING,
  evaluator_version STRING,

  -- Optional linkage to MLflow
  mlflow_run_id STRING,

  match_outcome STRING,
  overall_score DOUBLE,
  drift_score DOUBLE,
  coherence_score DOUBLE,
  idempotency_score DOUBLE,

  -- Optional artifact linkage (e.g. DBFS/Volumes/Cloud URI)
  artifact_uri STRING,

  metrics_json STRING,

  CONSTRAINT match_outcome_check CHECK (match_outcome IN ('match', 'mismatch', 'undetermined'))
)
USING DELTA;
