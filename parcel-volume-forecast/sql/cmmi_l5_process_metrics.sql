-- CMMI Level 5 process KPI view for ML lifecycle governance.
-- Assumes an operational run table exists with one row per training/evaluation run.
--
-- Interpretation notes:
-- 1) hours_to_baseline / hours_to_evaluation track process responsiveness, not model quality.
-- 2) artifact_completeness is binary (1.0/0.0) and should be interpreted as required-evidence readiness.
-- 3) baseline_speed_pass_rate and evaluation_speed_pass_rate use Phase 1 thresholds
--    (<= 2h baseline, <= 24h evaluation) and should be reviewed with requirement gate settings.
-- 4) promotion_rate is a process outcome indicator and should not be used alone for go/no-go decisions.
--
-- This view supports governance reporting by summarizing run-level metrics and
-- mapping them to the CMMI L5 artifact and gate pass criteria.

CREATE OR REPLACE VIEW cent_analytics_gold.vw_cmmi_l5_ml_process_metrics AS
WITH base AS (
    SELECT
        run_id,
        model_name,
        dataset_version,
        experiment_start_ts,
        baseline_ready_ts,
        evaluation_complete_ts,
        drift_detected_ts,
        prediction_shift_start_ts,
        promoted_flag,
        artifacts_complete_flag
    FROM cent_analytics_gold.ml_run_governance_log
),
calc AS (
    SELECT
        run_id,
        model_name,
        dataset_version,
        (unix_timestamp(baseline_ready_ts) - unix_timestamp(experiment_start_ts)) / 3600.0 AS hours_to_baseline,
        (unix_timestamp(evaluation_complete_ts) - unix_timestamp(experiment_start_ts)) / 3600.0 AS hours_to_evaluation,
        CASE WHEN artifacts_complete_flag THEN 1.0 ELSE 0.0 END AS artifact_completeness,
        CASE WHEN promoted_flag THEN 1 ELSE 0 END AS promoted_indicator,
        CASE
            WHEN drift_detected_ts IS NULL OR prediction_shift_start_ts IS NULL THEN NULL
            ELSE (unix_timestamp(drift_detected_ts) - unix_timestamp(prediction_shift_start_ts)) / 3600.0
        END AS drift_detection_latency_hours
    FROM base
)
SELECT
    model_name,
    dataset_version,
    COUNT(*) AS run_count,
    AVG(hours_to_baseline) AS avg_hours_to_baseline,
    AVG(hours_to_evaluation) AS avg_hours_to_evaluation,
    AVG(artifact_completeness) AS avg_artifact_completeness,
    AVG(promoted_indicator) AS promotion_rate,
    AVG(drift_detection_latency_hours) AS avg_drift_detection_latency_hours,
    SUM(CASE WHEN hours_to_baseline <= 2.0 THEN 1 ELSE 0 END) / COUNT(*) AS baseline_speed_pass_rate,
    SUM(CASE WHEN hours_to_evaluation <= 24.0 THEN 1 ELSE 0 END) / COUNT(*) AS evaluation_speed_pass_rate
FROM calc
GROUP BY model_name, dataset_version;
