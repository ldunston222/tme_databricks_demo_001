-- Observation Deck: Databricks SQL queries for datamodel_db
-- Replace 14 DAYS with your desired lookback.

-- 1) Outcomes over time (daily)
WITH base AS (
  SELECT date_trunc('DAY', created_at) AS day, status
  FROM datamodel_db.episode
  WHERE created_at >= current_timestamp() - INTERVAL 14 DAYS
)
SELECT
  day,
  SUM(CASE WHEN status = 'successful' THEN 1 ELSE 0 END) AS successful,
  SUM(CASE WHEN status = 'degraded' THEN 1 ELSE 0 END) AS degraded,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
  COUNT(*) AS total,
  ROUND(SUM(CASE WHEN status = 'successful' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 4) AS success_rate
FROM base
GROUP BY day
ORDER BY day;

-- 2) Token/cost efficiency by status
SELECT
  status,
  COUNT(*) AS episodes,
  ROUND(AVG(total_tokens), 2) AS avg_total_tokens,
  ROUND(AVG(input_tokens), 2) AS avg_input_tokens,
  ROUND(AVG(output_tokens), 2) AS avg_output_tokens,
  ROUND(AVG(duration_ms), 1) AS avg_duration_ms,
  ROUND(AVG(cost_usd), 6) AS avg_cost_usd,
  ROUND(SUM(cost_usd), 6) AS total_cost_usd
FROM datamodel_db.episode
WHERE created_at >= current_timestamp() - INTERVAL 14 DAYS
GROUP BY status
ORDER BY episodes DESC;

-- 3) Cost per successful episode
SELECT
  ROUND(SUM(cost_usd) / NULLIF(SUM(CASE WHEN status='successful' THEN 1 ELSE 0 END), 0), 6) AS cost_per_successful_episode_usd,
  ROUND(SUM(total_tokens) / NULLIF(SUM(CASE WHEN status='successful' THEN 1 ELSE 0 END), 0), 2) AS tokens_per_successful_episode
FROM datamodel_db.episode
WHERE created_at >= current_timestamp() - INTERVAL 14 DAYS;

-- 4) Drift vs golden (by day and golden_template_id)
-- Set threshold here.
WITH joined AS (
  SELECT
    e.created_at,
    e.episode_id,
    e.episode_version,
    e.golden_template_id,
    e.is_golden,
    ev.drift_score
  FROM datamodel_db.episode e
  LEFT JOIN datamodel_db.episode_evaluation ev
    ON e.episode_id = ev.episode_id AND e.episode_version = ev.episode_version
  WHERE e.created_at >= current_timestamp() - INTERVAL 14 DAYS
)
SELECT
  date_trunc('DAY', created_at) AS day,
  golden_template_id,
  ROUND(AVG(CASE WHEN is_golden THEN drift_score END), 4) AS avg_golden_drift,
  ROUND(AVG(CASE WHEN NOT is_golden THEN drift_score END), 4) AS avg_non_golden_drift,
  SUM(CASE WHEN NOT is_golden AND drift_score IS NOT NULL AND drift_score > 0.20 THEN 1 ELSE 0 END) AS drift_alerts,
  SUM(CASE WHEN NOT is_golden THEN 1 ELSE 0 END) AS non_golden_episodes
FROM joined
GROUP BY day, golden_template_id
ORDER BY day, golden_template_id;

-- 5) Failure clustering (degraded/failed) by step and annotation
WITH failed_eps AS (
  SELECT episode_id, episode_version
  FROM datamodel_db.episode
  WHERE created_at >= current_timestamp() - INTERVAL 14 DAYS
    AND status IN ('degraded', 'failed')
)
SELECT
  s.step_index,
  s.step_name,
  s.failure_type,
  s.invariant_violated,
  COUNT(*) AS occurrences
FROM datamodel_db.episode_steps s
JOIN failed_eps e
  ON s.episode_id = e.episode_id AND s.episode_version = e.episode_version
WHERE s.failure_type IS NOT NULL OR s.invariant_violated IS NOT NULL
GROUP BY s.step_index, s.step_name, s.failure_type, s.invariant_violated
ORDER BY occurrences DESC;

-- 6) Golden deltas (median current vs median golden) per step_key
WITH joined AS (
  SELECT
    e.golden_template_id,
    e.is_golden,
    COALESCE(s.step_name, CONCAT('step_', CAST(s.step_index AS STRING))) AS step_key,
    s.total_tokens,
    s.latency_ms,
    s.score
  FROM datamodel_db.episode e
  JOIN datamodel_db.episode_steps s
    ON e.episode_id = s.episode_id AND e.episode_version = s.episode_version
  WHERE e.created_at >= current_timestamp() - INTERVAL 14 DAYS
    AND e.golden_template_id IS NOT NULL
),
aggs AS (
  SELECT
    golden_template_id,
    step_key,
    percentile_approx(CASE WHEN is_golden THEN total_tokens END, 0.5) AS p50_tokens_golden,
    percentile_approx(CASE WHEN NOT is_golden THEN total_tokens END, 0.5) AS p50_tokens_current,
    percentile_approx(CASE WHEN is_golden THEN latency_ms END, 0.5) AS p50_latency_golden,
    percentile_approx(CASE WHEN NOT is_golden THEN latency_ms END, 0.5) AS p50_latency_current,
    percentile_approx(CASE WHEN is_golden THEN score END, 0.5) AS p50_score_golden,
    percentile_approx(CASE WHEN NOT is_golden THEN score END, 0.5) AS p50_score_current
  FROM joined
  GROUP BY golden_template_id, step_key
)
SELECT
  golden_template_id,
  step_key,
  p50_tokens_golden,
  p50_tokens_current,
  (p50_tokens_current - p50_tokens_golden) AS delta_tokens,
  p50_latency_golden,
  p50_latency_current,
  (p50_latency_current - p50_latency_golden) AS delta_latency_ms,
  p50_score_golden,
  p50_score_current,
  (p50_score_current - p50_score_golden) AS delta_score
FROM aggs
ORDER BY golden_template_id, step_key;

-- 7) Single-episode timeline (replace EPISODE_ID)
-- SELECT * FROM datamodel_db.episode WHERE episode_id = '<EPISODE_ID>' ORDER BY episode_version DESC;
-- SELECT * FROM datamodel_db.episode_steps WHERE episode_id = '<EPISODE_ID>' ORDER BY episode_version DESC, step_index ASC;
-- SELECT * FROM datamodel_db.episode_evaluation WHERE episode_id = '<EPISODE_ID>' ORDER BY evaluated_at DESC;
