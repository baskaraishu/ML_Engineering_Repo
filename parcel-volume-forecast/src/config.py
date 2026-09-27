"""Central configuration for the parcel-volume-forecast training pipeline.

All tunable values are defined here, grouped by purpose. Import from this
module rather than hardcoding values in individual modules.

The refinery guardrail defaults below are intentionally centralized so the
Stage 2/Stage 3 contract can be tuned in one place when the live-table source
changes or when the expected training volume shifts.
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
# Single runtime switch for training input mode.
# Supported values: "csv" or "live_table".
DEFAULT_INPUT_SOURCE_MODE: str = "live_table"

# CSV default used when DEFAULT_INPUT_SOURCE_MODE == "csv" and no
# --input-csv override is provided.
DEFAULT_SOURCE_CSV_PATH: str = "data/multi_client_ib_uplift.csv"

DEFAULT_SOURCE_TABLE: str = "evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35"
SOURCE_TABLE_ENV_VAR: str = "PARCEL_FORECAST_SOURCE_TABLE"

# Number of calendar days of history to pull when reading from a live table.
# Prevents OOM when the full table is larger than driver memory.
# Must exceed VAL_DAYS + TEST_DAYS (84) to leave training data.
# 730 days (2 full annual cycles) is preferred so XGBoost sees each seasonal
# pattern twice — Christmas, Easter, and bank-holiday splits are more robust
# when the model has seen the same calendar position in two different years.
TRAINING_LOOKBACK_DAYS: int = 730

# ---------------------------------------------------------------------------
# Refinery guardrail defaults
# Recalibrate REFINERY_EXPECTED_ROW_COUNT when the source table or lookback
# window changes.  Derivation: observe valid_rows from the first successful
# live-table run and set this to that value.
# 2026-07-06 calibration: 365-day window → ~572K valid rows; 730-day window
# (current) → ~1.14M rows (estimated as 2× the 365-day count).
# ---------------------------------------------------------------------------
REFINERY_EXPECTED_ROW_COUNT: int = 1_100_000
REFINERY_MIN_ROW_FRACTION: float = 0.50
REFINERY_MAX_DROP_FRACTION: float = 0.92
REFINERY_NOMINAL_DROP_FRAC: float = 0.02

# ---------------------------------------------------------------------------
# Operational archetype thresholds for Stage 3 promotion gating
# Values are tuned to warehouse workflow tolerance by cohort:
# - Anchors: strict, depot staffing-critical accounts
# - Dials: moderate, contractual schedule-balancing accounts
# - Spikers: wider tolerance, high-volatility surge accounts
# - Phantoms: loose tolerance, low-volume noisy long tail
# ---------------------------------------------------------------------------
MAX_ANCHOR_SMAPE: float = 7.5
MAX_DIAL_SMAPE: float = 13.0
MAX_SPIKER_SMAPE: float = 24.0
MAX_PHANTOM_SMAPE: float = 32.0

# Cohort cut points used to map rows into operational client archetypes.
ARCHETYPE_HIGH_VOLUME_QUANTILE: float = 0.75
ARCHETYPE_LOW_VOLUME_QUANTILE: float = 0.35
ARCHETYPE_LOW_PREDICTABILITY_QUANTILE: float = 0.65
ARCHETYPE_HIGH_PREDICTABILITY_QUANTILE: float = 0.35

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
# Calibrated against live-table naive baseline SMAPE of ~33.7% (daily client-level).
# Threshold is set 6pp above naive, so a model that is materially worse than naive
# (>40%) still fails, while a competitive model that beats or matches naive passes.
# ---------------------------------------------------------------------------
MAX_SMAPE_THRESHOLD: float = 40.0  # percent; run rejected if test_smape_volume > this

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
DATABRICKS_JOB_ID: int = 745290703540915

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
