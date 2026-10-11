"""Central configuration for the parcel-volume-forecast training pipeline.

This project is intentionally kept technology-neutral so it can be shared in a
personal repository without exposing organization-specific infrastructure.
"""

# ---------------------------------------------------------------------------
# Data columns
# ---------------------------------------------------------------------------
DATE_COL: str = "event_date"
ACTUAL_COL: str = "actual_volume"
BASELINE_COL: str = "rolling_4w_median"
TARGET_COL: str = "target"

# ---------------------------------------------------------------------------
# Data filtering
# ---------------------------------------------------------------------------
MIN_CLIENT_MEDIAN_VOLUME: int = 10

# ---------------------------------------------------------------------------
# Runtime table source defaults
# ---------------------------------------------------------------------------
DEFAULT_INPUT_SOURCE_MODE: str = "csv"
DEFAULT_SOURCE_CSV_PATH: str = "data/multi_client_ib_uplift.csv"
DEFAULT_SOURCE_TABLE: str = "catalog.schema.parcel_volume_training_table"
SOURCE_TABLE_ENV_VAR: str = "PARCEL_FORECAST_SOURCE_TABLE"
TRAINING_LOOKBACK_DAYS: int = 730

# ---------------------------------------------------------------------------
# Refinery guardrail defaults
# ---------------------------------------------------------------------------
REFINERY_EXPECTED_ROW_COUNT: int = 1_100_000
REFINERY_MIN_ROW_FRACTION: float = 0.50
REFINERY_MAX_DROP_FRACTION: float = 0.92
REFINERY_NOMINAL_DROP_FRAC: float = 0.02

# ---------------------------------------------------------------------------
# Operational archetype thresholds
# ---------------------------------------------------------------------------
MAX_ANCHOR_SMAPE: float = 7.5
MAX_DIAL_SMAPE: float = 13.0
MAX_SPIKER_SMAPE: float = 24.0
MAX_PHANTOM_SMAPE: float = 32.0
ARCHETYPE_HIGH_VOLUME_QUANTILE: float = 0.75
ARCHETYPE_LOW_VOLUME_QUANTILE: float = 0.35
ARCHETYPE_LOW_PREDICTABILITY_QUANTILE: float = 0.65
ARCHETYPE_HIGH_PREDICTABILITY_QUANTILE: float = 0.35

# ---------------------------------------------------------------------------
# Train / validation / test split
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
# ---------------------------------------------------------------------------
MAX_SMAPE_THRESHOLD: float = 40.0

# ---------------------------------------------------------------------------
# Governance gates
# ---------------------------------------------------------------------------
CMMI_MAX_BASELINE_HOURS: float = 2.0
CMMI_MAX_EVAL_HOURS: float = 24.0

# ---------------------------------------------------------------------------
# Model identity
# ---------------------------------------------------------------------------
MODEL_NAME: str = "XGBoost_MultiClient_Forecast_Analysis"
DEFAULT_DATASET_VERSION: str = "v1"
DEFAULT_EXPERIMENT_NAME: str = "/Shared/forecasting/parcel-volume-forecast"

# ---------------------------------------------------------------------------
# Databricks / orchestration placeholders
# ---------------------------------------------------------------------------
DATABRICKS_JOB_ID: int = 0
DEFAULT_DATABRICKS_WORKSPACE_REPO_ROOT: str = "/Workspace/Repos/<your-user>/parcel-volume-forecast"
DEFAULT_DATABRICKS_PHASE0_FALLBACK_CLUSTER_ID: str = "<cluster-id>"
