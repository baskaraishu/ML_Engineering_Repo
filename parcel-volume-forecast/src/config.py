"""Central configuration for the parcel-volume-forecast training pipeline.

All tunable values are defined here, grouped by purpose.
Import from this module rather than hardcoding values in individual modules.
"""

# ---------------------------------------------------------------------------
# Data columns
# Column names expected in the training CSV.
# ---------------------------------------------------------------------------
DATE_COL: str = "event_date"
ACTUAL_COL: str = "actual_volume"
BASELINE_COL: str = "rolling_4w_median"
TARGET_COL: str = "target"

# ---------------------------------------------------------------------------
# Data filtering
# Minimum median daily volume for a client to be included in training.
# ---------------------------------------------------------------------------
MIN_CLIENT_MEDIAN_VOLUME: int = 10

# ---------------------------------------------------------------------------
# Runtime table source defaults
# Phase 0: centralize runtime table names so they are not hardcoded in
# orchestration code. Local/preflight runs may use these defaults.
# ---------------------------------------------------------------------------
DEFAULT_SOURCE_TABLE: str = "evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_ib_uplift"
SOURCE_TABLE_ENV_VAR: str = "PARCEL_FORECAST_SOURCE_TABLE"

# ---------------------------------------------------------------------------
# Train / validation / test split
# Number of calendar days reserved for each held-out window.
# ---------------------------------------------------------------------------
TEST_DAYS: int = 42
VAL_DAYS: int = 42

# ---------------------------------------------------------------------------
# XGBoost hyperparameters
# ---------------------------------------------------------------------------
XGB_N_ESTIMATORS: int = 600
XGB_MAX_DEPTH: int = 8
XGB_LEARNING_RATE: float = 0.03
XGB_SUBSAMPLE: float = 0.85
XGB_COLSAMPLE_BYTREE: float = 0.85
XGB_RANDOM_STATE: int = 42

# ---------------------------------------------------------------------------
# Evaluation quality gate
# Maximum allowed SMAPE on the test split for model promotion.
# ---------------------------------------------------------------------------
MAX_SMAPE_THRESHOLD: float = 15.0  # percent; run rejected if test_smape_target > this

# ---------------------------------------------------------------------------
# CMMI L5 process gates
# Speed and completeness thresholds for governance gate evaluation.
# See src/governance/cmmi_l5_metrics.py — cmmi_l5_gate_status().
# ---------------------------------------------------------------------------
CMMI_MAX_BASELINE_HOURS: float = 2.0   # baseline_speed_pass: data+features ready within 2 hours
CMMI_MAX_EVAL_HOURS: float = 24.0      # evaluation_speed_pass: full evaluation complete within 24 hours

# ---------------------------------------------------------------------------
# Model identity
# ---------------------------------------------------------------------------
MODEL_NAME: str = "XGBoost_MultiClient_Forecast_IB_Uplift_Analysis"
DEFAULT_DATASET_VERSION: str = "v1"
DEFAULT_EXPERIMENT_NAME: str = "/Shared/forecasting/parcel-volume-forecast"

# ---------------------------------------------------------------------------
# Databricks job identity
# ---------------------------------------------------------------------------
# Used by CLI/REST examples and automation helpers that need the numeric job id.
DATABRICKS_JOB_ID: int = 587032785657077

# ---------------------------------------------------------------------------
# Databricks workspace repo mapping
# ---------------------------------------------------------------------------
# This must point to the Databricks workspace repo root that contains this
# repository when deploying jobs via direct CLI/API reset rather than a bundle.
# NOTE: Update this to your actual workspace repo path before deployment.
DEFAULT_DATABRICKS_WORKSPACE_REPO_ROOT: str = "/Workspace/Repos/service-principal@evri.com/parcel-volume-forecast"

# ---------------------------------------------------------------------------
# Databricks Phase 0 compute fallback
# ---------------------------------------------------------------------------
# Temporary fallback cluster that is known to run notebook experiments and can
# be used to unblock job-triggered validation when job-compute permissions are
# still being provisioned.
# NOTE: Update this to your actual cluster ID before Phase 0 debugging.
DEFAULT_DATABRICKS_PHASE0_FALLBACK_CLUSTER_ID: str = "0701-234651-abc1def2"
