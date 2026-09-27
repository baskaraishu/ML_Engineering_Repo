from __future__ import annotations

import argparse
import inspect
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

"""Phase 1 training entrypoint with MLflow and CMMI process evidence capture.

Inputs:
- CSV path containing time-series features and baseline columns
- MLflow experiment name
- dataset version label for traceability

Outputs:
- model artifact in MLflow
- validation/test SMAPE metrics
- CMMI process metrics and gate flags used in phase-governance reviews
"""

import mlflow
import pandas as pd


def _resolve_project_root() -> Path:
    candidate_paths: list[Path] = []
    if "__file__" in globals():
        candidate_paths.append(Path(__file__).resolve())

    current_frame = inspect.currentframe()
    if current_frame is not None:
        candidate_paths.append(Path(current_frame.f_code.co_filename).resolve())

    candidate_paths.append(Path(os.getcwd()).resolve())

    for candidate in candidate_paths:
        search_roots = [candidate] if candidate.is_dir() else candidate.parents
        for root in search_roots:
            if (root / "src" / "config.py").exists():
                return root

    return Path(os.getcwd()).resolve()


PROJECT_ROOT = _resolve_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    CMMI_MAX_BASELINE_HOURS,
    CMMI_MAX_EVAL_HOURS,
    DATE_COL,
    ACTUAL_COL,
    BASELINE_COL,
    TARGET_COL,
    TEST_DAYS,
    VAL_DAYS,
    MAX_SMAPE_THRESHOLD,
    MODEL_NAME,
    DEFAULT_DATASET_VERSION,
    DEFAULT_EXPERIMENT_NAME,
)
from src.evaluation.metrics import smape
from src.features.target_transform import build_uplift_target
from src.features.time_features import add_cyclical_time_features
from src.governance.cmmi_l5_metrics import CmmiRunRecord, cmmi_l5_gate_status
from src.training.data_validation import validate_input_dataframe
from src.training.feature_selection import infer_feature_columns
from src.training.model_factory import build_xgb_regressor
from src.training.reporting import emit_training_run_report
from src.training.splitting import split_train_val_test
from src.training.train_config import TrainConfig

if TYPE_CHECKING:
    from xgboost import XGBRegressor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _validate_input_dataframe(df: pd.DataFrame, cfg: TrainConfig) -> None:
    """Backward-compatible wrapper for the extracted validation helper."""
    validate_input_dataframe(df, cfg)


def _infer_feature_columns(df: pd.DataFrame, cfg: TrainConfig) -> list[str]:
    """Backward-compatible wrapper for the extracted feature-selection helper."""
    return infer_feature_columns(df, cfg)


def run_training(
    input_csv: str,
    experiment_name: str,
    dataset_version: str = "v1",
    run_mode: str = "production",
) -> None:
    """Run the Phase 1 training experiment and log MLflow/CMMI metrics.

    This entrypoint reads the training CSV, constructs uplift targets and
    cyclical time features, trains an XGBoost model, evaluates held-out data,
    and emits governance evidence for CMMI L5 process gates.
    
    Call sequence (all steps in this single function):
    1. Load CSV
    2. Validate input → _validate_input_dataframe()
    3. Add time features → add_cyclical_time_features()
    4. Build uplift target → build_uplift_target()
    5. Infer features → _infer_feature_columns()
    6. Split data → split_train_val_test()
    7. Train XGBoost → xgb.fit()
    8. Evaluate → smape()
    9. Log core run outputs to MLflow
    10. Compute CMMI gate status
    11. Generate structured run report artifacts
    """
    normalized_run_mode = run_mode.strip().lower()
    if normalized_run_mode not in {"production", "debug"}:
        raise ValueError("run_mode must be either 'production' or 'debug'.")

    experiment_start = datetime.utcnow()  # CMMI metric: marks the start of the run for baseline_speed and evaluation_speed calculations
    cfg = TrainConfig(dataset_version=dataset_version)

    # STEP 1: Load training data
    logger.info("Loading training data from %s", input_csv)
    df = pd.read_csv(input_csv)
    if df.empty:
        raise ValueError("Input training CSV is empty.")

    if cfg.date_col not in df.columns:
        raise ValueError(f"Missing required date column '{cfg.date_col}' in input CSV.")
    df[cfg.date_col] = pd.to_datetime(df[cfg.date_col], errors="coerce")

    # STEP 2: Validate input data — stops pipeline if validation fails
    validate_input_dataframe(df, cfg)
    
    # STEP 3: Transform features
    df = add_cyclical_time_features(df, cfg.date_col)
    df[cfg.target_col] = build_uplift_target(df, cfg.actual_col, cfg.baseline_col)

    # STEP 4a: Infer feature columns
    feature_cols = infer_feature_columns(df, cfg)
    logger.info("Using %d feature columns for training: %s", len(feature_cols), feature_cols)

    # STEP 4b: Split into train/val/test
    train, val, test = split_train_val_test(df, cfg.date_col, cfg.test_days, cfg.val_days)

    # STEP 4c: Train XGBoost
    xgb = build_xgb_regressor()

    baseline_ready = datetime.utcnow()  # CMMI metric: marks when data+features are ready; used to compute baseline_speed (threshold ≤ 2h)

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="xgb_multi_client_ib_uplift") as run:
        mlflow.set_tag("run_mode", normalized_run_mode)
        mlflow.log_param("run_mode", normalized_run_mode)

        xgb.fit(train[feature_cols], train[cfg.target_col])

        # STEP 5: Evaluate on validation and test
        val_pred = xgb.predict(val[feature_cols])
        test_pred = xgb.predict(test[feature_cols])

        val_smape = smape(val[cfg.target_col].values, val_pred)
        test_smape = smape(test[cfg.target_col].values, test_pred)

        # STEP 6: Log core metrics, params, and model to MLflow
        mlflow.log_metric("val_smape_target", val_smape)
        mlflow.log_metric("test_smape_target", test_smape)
        mlflow.log_param("feature_count", len(feature_cols))
        mlflow.log_param("test_days", cfg.test_days)
        mlflow.log_param("val_days", cfg.val_days)
        mlflow.log_param("dataset_version", cfg.dataset_version)
        mlflow.log_param("model_name", cfg.model_name)

        mlflow.xgboost.log_model(xgb, artifact_path="model")

        evaluation_complete = datetime.utcnow()  # CMMI metric: marks end of evaluation; used to compute evaluation_speed (threshold ≤ 24h)

        # STEP 7: Compute CMMI governance metrics and gate status
        gov_record = CmmiRunRecord(
            run_id=run.info.run_id,
            model_name=cfg.model_name,
            dataset_version=cfg.dataset_version,
            experiment_start=experiment_start,
            baseline_ready=baseline_ready,
            evaluation_complete=evaluation_complete,
            promoted=False,           # CMMI metric: updated to True only after human review and go/no-go decision
            artifacts_complete=True,  # CMMI metric: True because mlflow.xgboost.log_model() was called above
        )
        gates = cmmi_l5_gate_status(gov_record, max_baseline_hours=CMMI_MAX_BASELINE_HOURS, max_eval_hours=CMMI_MAX_EVAL_HOURS)

        mlflow.log_metric("cmmi_hours_to_baseline", hours_to_baseline := (baseline_ready - experiment_start).total_seconds() / 3600.0)
        mlflow.log_metric("cmmi_hours_to_evaluation", hours_to_evaluation := (evaluation_complete - experiment_start).total_seconds() / 3600.0)
        mlflow.log_metric("cmmi_artifact_completeness", 1.0 if gov_record.artifacts_complete else 0.0)
        mlflow.log_param("cmmi_baseline_speed_pass", gates["baseline_speed_pass"])    # True if ≤ 2.0 hours
        mlflow.log_param("cmmi_evaluation_speed_pass", gates["evaluation_speed_pass"])  # True if ≤ 24.0 hours
        mlflow.log_param("cmmi_artifact_completeness_pass", gates["artifact_completeness_pass"])  # True if model artifact logged

        quality_pass = test_smape <= MAX_SMAPE_THRESHOLD
        promotion_recommendation = quality_pass and all(gates.values())
        if normalized_run_mode == "debug":
            logger.warning("Debug run_mode enabled; promotion recommendation is forced to False.")
            promotion_recommendation = False
            mlflow.log_param("promotion_evidence_allowed", False)
        else:
            mlflow.log_param("promotion_evidence_allowed", True)
        mlflow.log_param("quality_pass", quality_pass)
        mlflow.log_param("promotion_recommendation", promotion_recommendation)

        # STEP 8: Generate and log structured report artifacts for leadership and audit consumption.
        emit_training_run_report(
            run_id=run.info.run_id,
            run_name="xgb_multi_client_ib_uplift",
            cfg=cfg,
            test_smape_target=test_smape,
            val_smape_target=val_smape,
            cmmi_hours_to_baseline=hours_to_baseline,
            cmmi_hours_to_evaluation=hours_to_evaluation,
            cmmi_artifact_completeness=1.0 if gov_record.artifacts_complete else 0.0,
            cmmi_gates=gates,
            artifact_path="reports",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT_NAME)
    parser.add_argument("--dataset-version", default=DEFAULT_DATASET_VERSION)
    parser.add_argument("--run-mode", default="production", choices=["production", "debug"])
    args = parser.parse_args()

    run_training(args.input_csv, args.experiment, args.dataset_version, args.run_mode)
