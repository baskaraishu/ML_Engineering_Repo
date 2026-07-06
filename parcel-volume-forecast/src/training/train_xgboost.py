from __future__ import annotations

import argparse
import inspect
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

"""Phase 1 training entrypoint with MLflow and CMMI process evidence capture.

Inputs:
- CSV path containing time-series features and baseline columns
- MLflow experiment name
- dataset version label for traceability
- optional Unity Catalog table source for live-table training

Outputs:
- model artifact in MLflow
- validation/test SMAPE metrics
- CMMI process metrics and gate flags used in phase-governance reviews

The loader applies the staged refinery contract before training: Stage 2
filters and projects the live-table rows in a bounded, validated slice, and
Stage 3 evaluates whether the filtered volume remains within the approved
operational tolerance envelope.
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
    DEFAULT_INPUT_SOURCE_MODE,
    DEFAULT_SOURCE_CSV_PATH,
    DEFAULT_SOURCE_TABLE,
    ARCHETYPE_HIGH_PREDICTABILITY_QUANTILE,
    ARCHETYPE_HIGH_VOLUME_QUANTILE,
    ARCHETYPE_LOW_PREDICTABILITY_QUANTILE,
    ARCHETYPE_LOW_VOLUME_QUANTILE,
    MAX_ANCHOR_SMAPE,
    MAX_DIAL_SMAPE,
    MAX_PHANTOM_SMAPE,
    MAX_SPIKER_SMAPE,
    MIN_CLIENT_MEDIAN_VOLUME,
    REFINERY_EXPECTED_ROW_COUNT,
    SOURCE_TABLE_ENV_VAR,
    TRAINING_LOOKBACK_DAYS,
)
from src.evaluation.metrics import smape
from src.features.target_transform import build_uplift_target, invert_uplift_target
from src.features.time_features import add_cyclical_time_features
from src.governance.cmmi_l5_metrics import CmmiRunRecord, cmmi_l5_gate_status
from src.training.data_validation import validate_input_dataframe
from src.training.feature_selection import infer_feature_columns
from src.training.model_factory import build_xgb_regressor
from src.training.refinery import apply_refinery_filters_to_pandas, evaluate_refinery_guardrail
from src.training.reporting import emit_training_run_report
from src.training.splitting import split_train_val_test
from src.training.train_config import TrainConfig

if TYPE_CHECKING:
    from xgboost import XGBRegressor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _is_unity_catalog_table(input_source: str) -> bool:
    """Detect if an input source string is a Unity Catalog table name."""

    return (
        not input_source.endswith(".csv")
        and "." in input_source
        and "/" not in input_source.replace("\\", "/")
    )


def _assign_operational_archetypes(
    df: pd.DataFrame,
    ref_df: pd.DataFrame | None = None,
) -> pd.Series:
    """Assign each row to an operational client archetype for logistics gating.

    Quantile cutpoints are derived from ref_df (training data) so that archetype
    boundaries are stable across train/val/test splits.  When ref_df is not
    supplied the function falls back to df itself (CSV / smoke-test mode).
    """
    ref = ref_df if ref_df is not None else df

    baseline = pd.to_numeric(df[BASELINE_COL], errors="coerce").fillna(0.0)
    actual = pd.to_numeric(df[ACTUAL_COL], errors="coerce").fillna(0.0)
    china_flag = pd.to_numeric(df["is_china"], errors="coerce").fillna(0.0) if "is_china" in df.columns else pd.Series(0.0, index=df.index)
    predictability_signal = ((actual - baseline).abs() / baseline.replace(0, pd.NA)).fillna(0.0)

    # Derive stable cutpoints from training-period distribution, not from the
    # test window — prevents test-period anomalies from shifting archetype labels.
    ref_baseline = pd.to_numeric(ref[BASELINE_COL], errors="coerce").fillna(0.0)
    ref_actual = pd.to_numeric(ref[ACTUAL_COL], errors="coerce").fillna(0.0)
    ref_predictability = ((ref_actual - ref_baseline).abs() / ref_baseline.replace(0, pd.NA)).fillna(0.0)

    high_volume_cut = float(ref_baseline.quantile(ARCHETYPE_HIGH_VOLUME_QUANTILE))
    low_volume_cut = float(ref_baseline.quantile(ARCHETYPE_LOW_VOLUME_QUANTILE))
    low_predictability_cut = float(ref_predictability.quantile(ARCHETYPE_LOW_PREDICTABILITY_QUANTILE))
    high_predictability_cut = float(ref_predictability.quantile(ARCHETYPE_HIGH_PREDICTABILITY_QUANTILE))

    high_volume = baseline >= high_volume_cut
    low_volume = baseline <= low_volume_cut
    low_predictability = (predictability_signal >= low_predictability_cut) | (china_flag > 0)
    high_predictability = (predictability_signal <= high_predictability_cut) & (china_flag <= 0)

    cohort = pd.Series("The Dials", index=df.index, dtype="object")
    cohort.loc[high_volume & high_predictability] = "The Anchors"
    cohort.loc[high_volume & low_predictability] = "The Spikers"
    cohort.loc[low_volume] = "The Phantoms"
    return cohort


def _evaluate_operational_archetype_gates(
    test_df: pd.DataFrame,
    pred_volume: pd.Series,
    train_df: pd.DataFrame | None = None,
) -> tuple[bool, list[dict[str, Any]], str | None, bool]:
    """Evaluate cohort-level gates and return promotion decision telemetry.

    SMAPE is computed on the DAILY AGGREGATE volume per cohort, not on
    individual client-day rows.  For a global model serving a multi-client
    live table this is the operationally meaningful metric: planners act on
    the total volume contributed by each cohort per day, not on per-row noise.

    train_df is used to derive stable archetype quantile cutpoints so that
    archetype boundaries are anchored to the training distribution and do not
    shift with test-window anomalies.

    Returns:
        quality_pass: hard gate status used for promotion blocking.
        archetype_ledger: operational briefing rows per cohort.
        promotion_block_reason: explicit rejection reason when blocked.
        deviation_warning: True when only warning-level cohort deviations occur.
    """

    archetypes = _assign_operational_archetypes(test_df, ref_df=train_df)
    threshold_by_archetype = {
        "The Anchors": MAX_ANCHOR_SMAPE,
        "The Dials": MAX_DIAL_SMAPE,
        "The Spikers": MAX_SPIKER_SMAPE,
        "The Phantoms": MAX_PHANTOM_SMAPE,
    }
    hard_gate_cohorts = {"The Anchors", "The Dials", "The Phantoms"}

    ledger: list[dict[str, Any]] = []
    quality_pass = True
    promotion_block_reason: str | None = None
    deviation_warning = False

    for cohort_name in ["The Anchors", "The Dials", "The Spikers", "The Phantoms"]:
        mask = archetypes == cohort_name
        threshold = threshold_by_archetype[cohort_name]

        if mask.sum() == 0:
            cohort_smape = float("nan")
            workflow_flag = "ZONE_1_NOMINAL"
            breached = False
        else:
            # Daily-aggregate SMAPE: sum all client volumes per date within the
            # cohort, then compute SMAPE across the test days.  This is the
            # planning-level metric; row-level SMAPE on a global model without
            # client features is dominated by inter-client noise and not
            # actionable for depot planning decisions.
            cohort_date = test_df.loc[mask, DATE_COL]
            daily_actual = test_df.loc[mask, ACTUAL_COL].groupby(cohort_date).sum()
            daily_pred = pred_volume.loc[mask].groupby(cohort_date).sum()
            cohort_smape = smape(daily_actual.values, daily_pred.values)
            breached = cohort_smape > threshold
            if breached and cohort_name in hard_gate_cohorts:
                workflow_flag = "ZONE_3_CRITICAL_REJECTION"
            elif breached:
                workflow_flag = "ZONE_2_DEVIATION_WARNING"
            else:
                workflow_flag = "ZONE_1_NOMINAL"

        if breached and cohort_name in hard_gate_cohorts:
            quality_pass = False
            if cohort_name == "The Anchors":
                promotion_block_reason = (
                    "CRITICAL REJECTION: Anchor cohort breached 8% floor tolerance. "
                    "Potential depot gridlock risk."
                )
            elif cohort_name == "The Dials":
                promotion_block_reason = (
                    "CRITICAL REJECTION: Dial cohort exceeded contractual throughput tolerance. "
                    "Courier schedule integrity at risk."
                )
            else:
                promotion_block_reason = (
                    "CRITICAL REJECTION: Phantom cohort exceeded loose long-tail tolerance. "
                    "Mixed cage planning reliability at risk."
                )
        elif breached and cohort_name == "The Spikers":
            deviation_warning = True

        ledger.append(
            {
                "archetype": cohort_name,
                "row_count": int(mask.sum()),
                "business_smape": None if pd.isna(cohort_smape) else float(cohort_smape),
                "threshold": float(threshold),
                "workflow_impact_flag": workflow_flag,
            }
        )

    return quality_pass, ledger, promotion_block_reason, deviation_warning


def _validate_input_dataframe(df: pd.DataFrame, cfg: TrainConfig) -> None:
    """Backward-compatible wrapper for the extracted validation helper."""
    validate_input_dataframe(df, cfg)


def _infer_feature_columns(df: pd.DataFrame, cfg: TrainConfig) -> list[str]:
    """Backward-compatible wrapper for the extracted feature-selection helper."""
    return infer_feature_columns(df, cfg)


def _load_training_data(input_source: str) -> pd.DataFrame:
    """Load training data from CSV file or Unity Catalog table.
    
    Args:
        input_source: Either a CSV file path (/path/to/file.csv) or a 
                      Unity Catalog table name (catalog.schema.table)
    
    Returns:
        DataFrame with loaded training data
        
    Raises:
        ValueError: If data is empty or table/file not found
    """
    logger.info("Loading training data from %s", input_source)
    
    # Detect if input is a table name (contains dots) or CSV file path
    is_table = _is_unity_catalog_table(input_source)
    
    if is_table:
        logger.info("Detected Unity Catalog table: %s", input_source)
        try:
            from pyspark.sql import SparkSession
            from pyspark.sql import functions as F
            from datetime import timedelta

            def _find_case_insensitive_column(columns: list[str], candidates: list[str]) -> str | None:
                lookup = {c.lower(): c for c in columns}
                for candidate in candidates:
                    resolved = lookup.get(candidate.lower())
                    if resolved:
                        return resolved
                return None

            spark = SparkSession.getActiveSession()
            if spark is None:
                raise RuntimeError("SparkSession not available. Cannot read from table in non-Databricks environment.")
            cutoff_date = (datetime.now() - timedelta(days=TRAINING_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
            spark_df = spark.table(input_source)

            # Resolve all required source column names before any filtering.
            col_candidates = {
                DATE_COL:      [DATE_COL, "preadvice_date", "DATE_DATE"],
                ACTUAL_COL:    [ACTUAL_COL, "parcel_volume"],
                BASELINE_COL:  [BASELINE_COL, "median_4wk_volume"],
                TARGET_COL:    [TARGET_COL],
                "is_china":    ["is_china", "china_flag"],
                "is_domestic": ["is_domestic", "domestic_flag"],
            }
            resolved: dict[str, str | None] = {
                tgt: _find_case_insensitive_column(spark_df.columns, aliases)
                for tgt, aliases in col_candidates.items()
            }
            required = [DATE_COL, ACTUAL_COL, BASELINE_COL, TARGET_COL]
            missing_cols = [r for r in required if resolved[r] is None]
            if missing_cols:
                raise ValueError(
                    f"Unable to resolve required columns in live table: {missing_cols}. "
                    f"Available columns: {spark_df.columns}"
                )

            # Push ALL Stage 2 predicates into Spark before toPandas() so the
            # driver only receives the model-ready slice.  Collecting the full
            # raw table causes OOM on Databricks serverless for large windows.
            logger.info(
                "Applying Spark-side Stage 2 push-down: %s >= '%s' (%d days) "
                "+ null/quality filters before toPandas()",
                resolved[DATE_COL], cutoff_date, TRAINING_LOOKBACK_DAYS,
            )
            select_exprs = [
                F.col(resolved[DATE_COL]).alias(DATE_COL),
                F.col(resolved[ACTUAL_COL]).alias(ACTUAL_COL),
                F.col(resolved[BASELINE_COL]).alias(BASELINE_COL),
                F.col(resolved[TARGET_COL]).alias(TARGET_COL),
            ]
            for flag_col in ("is_china", "is_domestic"):
                src = resolved[flag_col]
                if src:
                    select_exprs.append(F.col(src).alias(flag_col))
                else:
                    select_exprs.append(F.lit(0).alias(flag_col))

            # Collect event feature columns from the live table (e.g.
            # event_black_friday, event_christmas_day, event_eng_bank_holiday).
            # These binary calendar signals give the model explicit event-period
            # signal that cyclical features cannot capture precisely.
            # Exclude the 'events' ARRAY column — it cannot be cast to a scalar.
            event_feature_cols = [
                c for c in spark_df.columns
                if c.lower().startswith("event_") and c.lower() != "events"
            ]
            for ec in event_feature_cols:
                select_exprs.append(F.col(ec))
            if event_feature_cols:
                logger.info("Including %d event feature columns from live table", len(event_feature_cols))

            today_str = datetime.now().strftime("%Y-%m-%d")
            spark_df = (
                spark_df
                .select(*select_exprs)
                # Lower bound: only include rows within the training lookback window.
                .filter(F.to_date(F.col(DATE_COL)) >= F.lit(cutoff_date))
                # Upper bound: exclude future rows where parcel_volume=0 because
                # the event has not occurred yet.  Future rows corrupt the test
                # split and produce extreme log-uplift targets (~log(1e-6)=-13.8).
                .filter(F.to_date(F.col(DATE_COL)) <= F.lit(today_str))
                .filter(F.col(DATE_COL).isNotNull())
                .filter(F.col(ACTUAL_COL).isNotNull())
                # Exclude zero-volume rows: log(0/baseline) is undefined and is
                # clipped to log(1e-6)=-13.8, which severely biases the model.
                .filter(F.col(ACTUAL_COL).cast("double") > 0)
                .filter(F.col(BASELINE_COL).isNotNull())
                # TARGET_COL is excluded from the null filter: it is overwritten
                # by build_uplift_target() in run_training().
                .filter(F.col(BASELINE_COL).cast("double") > MIN_CLIENT_MEDIAN_VOLUME)
            )
            df = spark_df.toPandas()
            logger.info("Collected %d rows from live table after Spark-side Stage 2 push-down", len(df))
        except ImportError:
            raise RuntimeError("PySpark not available. Cannot read from Unity Catalog tables in local environment.")
    else:
        logger.info("Detected CSV file: %s", input_source)
        df = pd.read_csv(input_source)

    if df.empty:
        raise ValueError(f"Input data from {input_source} is empty.")

    filtered_df = apply_refinery_filters_to_pandas(df)
    if filtered_df.empty:
        raise ValueError(f"Refinery filters removed all rows from {input_source}.")

    # Merge event feature columns back from pre-refinery df by index.
    # The refinery returns only the 6 canonical schema columns; event columns
    # are preserved separately so they are available to infer_feature_columns().
    event_passthrough = [c for c in df.columns if c.startswith("event_")]
    if event_passthrough:
        # Use pd.to_numeric(errors='coerce') so any column that arrives as a
        # non-numeric type (e.g. datetime.date from certain Spark INT columns)
        # is coerced to NaN and then filled to 0 rather than raising TypeError.
        event_df = df[event_passthrough].apply(
            lambda s: pd.to_numeric(s, errors="coerce").fillna(0).astype("int8")
        )
        filtered_df = filtered_df.join(event_df)

    if is_table:
        guardrail = evaluate_refinery_guardrail(
            len(filtered_df),
            expected_row_count=REFINERY_EXPECTED_ROW_COUNT,
        )
        if guardrail.passed:
            if guardrail.failure_reason is None:
                logger.info(
                    "Stage 3 guardrail: %s (drop_frac=%.4f)",
                    guardrail.workflow_impact_flag,
                    guardrail.drop_frac,
                )
            else:
                logger.warning(
                    "Stage 3 guardrail: %s (drop_frac=%.4f, reason=%s)",
                    guardrail.workflow_impact_flag,
                    guardrail.drop_frac,
                    guardrail.failure_reason,
                )
        else:
            raise RuntimeError(
                f"Stage 3 guardrail failed for live-table input: {guardrail.failure_reason}"
            )

    return filtered_df


def _resolve_input_source(input_csv: str | None) -> str:
    """Resolve the effective training input source from CLI or config.

    Precedence:
    1. Explicit CLI --input-csv value
    2. Config switch DEFAULT_INPUT_SOURCE_MODE
       - csv -> DEFAULT_SOURCE_CSV_PATH
       - live_table -> SOURCE_TABLE_ENV_VAR or DEFAULT_SOURCE_TABLE
    """
    if input_csv:
        return input_csv

    source_mode = DEFAULT_INPUT_SOURCE_MODE.strip().lower()
    if source_mode == "csv":
        return DEFAULT_SOURCE_CSV_PATH
    if source_mode == "live_table":
        return os.getenv(SOURCE_TABLE_ENV_VAR, DEFAULT_SOURCE_TABLE)

    raise ValueError(
        "DEFAULT_INPUT_SOURCE_MODE must be either 'csv' or 'live_table'."
    )


def run_training(
    input_csv: str | None,
    experiment_name: str,
    dataset_version: str = "v1",
    run_mode: str = "production",
) -> None:
    """Run the Phase 1 training experiment and log MLflow/CMMI metrics.

    This entrypoint reads the training CSV or SQL table, constructs uplift targets 
    and cyclical time features, trains an XGBoost model, evaluates held-out data,
    and emits governance evidence for CMMI L5 process gates.
    
    Call sequence (all steps in this single function):
    1. Load CSV or table
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
    
    Parameters:
        input_csv: Optional CSV path or table name override. If omitted,
            source is selected by DEFAULT_INPUT_SOURCE_MODE in src/config.py.
        experiment_name: MLflow experiment name
        dataset_version: Version label for traceability
        run_mode: 'production' or 'debug'
    """
    normalized_run_mode = run_mode.strip().lower()
    if normalized_run_mode not in {"production", "debug"}:
        raise ValueError("run_mode must be either 'production' or 'debug'.")

    experiment_start = datetime.utcnow()  # CMMI metric: marks the start of the run for baseline_speed and evaluation_speed calculations
    cfg = TrainConfig(dataset_version=dataset_version)

    # STEP 1: Load training data (supports both CSV and Unity Catalog tables)
    effective_input_source = _resolve_input_source(input_csv)
    source_mode = "live_table" if _is_unity_catalog_table(effective_input_source) else "csv"
    logger.info("Resolved input source mode=%s source=%s", source_mode, effective_input_source)

    df = _load_training_data(effective_input_source)
    if df.empty:
        raise ValueError("Input training data is empty.")

    if cfg.date_col not in df.columns:
        raise ValueError(f"Missing required date column '{cfg.date_col}' in input data.")
    df[cfg.date_col] = pd.to_datetime(df[cfg.date_col], errors="coerce")

    # Drop rows where required columns are null (live tables may have sparse rows)
    required_cols = [cfg.date_col, cfg.actual_col, cfg.baseline_col]
    n_before = len(df)
    df = df.dropna(subset=required_cols)
    # Drop rows with non-positive baseline (zero-history clients are untrainable for uplift)
    df = df[df[cfg.baseline_col] > 0]
    n_dropped = n_before - len(df)
    if n_dropped:
        logger.info("Dropped %d rows with nulls or non-positive baseline in %s", n_dropped, required_cols)
    if df.empty:
        raise ValueError("Input training data is empty after dropping null rows.")

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
        mlflow.log_param("input_source_mode", source_mode)
        mlflow.log_param("input_source", effective_input_source)

        xgb.fit(train[feature_cols], train[cfg.target_col])

        # STEP 5: Evaluate on validation and test
        val_pred = xgb.predict(val[feature_cols])
        test_pred = xgb.predict(test[feature_cols])

        # Diagnostic metrics in transformed target-space (log-uplift).
        val_smape = smape(val[cfg.target_col].values, val_pred)
        test_smape = smape(test[cfg.target_col].values, test_pred)

        # Promotion metrics in business-space (absolute volume).
        val_pred_volume = invert_uplift_target(val_pred, val[cfg.baseline_col])
        test_pred_volume = invert_uplift_target(test_pred, test[cfg.baseline_col])
        val_smape_volume = smape(val[cfg.actual_col].values, val_pred_volume.values)
        test_smape_volume = smape(test[cfg.actual_col].values, test_pred_volume.values)

        # Naive baseline SMAPE: what SMAPE you'd get by predicting = baseline
        # (no model).  Logged for diagnostic comparison only.
        naive_test_smape_volume = smape(test[cfg.actual_col].values, test[cfg.baseline_col].values)
        logger.info(
            "Naive baseline SMAPE (test): %.2f%% | Model SMAPE (test): %.2f%%",
            naive_test_smape_volume, test_smape_volume,
        )

        archetype_quality_pass, archetype_ledger, promotion_block_reason, has_spiker_warning = (
            _evaluate_operational_archetype_gates(test, test_pred_volume, train_df=train)
        )

        for row in archetype_ledger:
            logger.info(
                "Stage 3 archetype ledger | %s | rows=%d | daily_agg_smape=%s | threshold=%.2f | flag=%s",
                row["archetype"],
                row["row_count"],
                "NA" if row["business_smape"] is None else f"{row['business_smape']:.3f}",
                row["threshold"],
                row["workflow_impact_flag"],
            )

        # STEP 6: Log core metrics, params, and model to MLflow
        mlflow.log_metric("val_smape_target", val_smape)
        mlflow.log_metric("test_smape_target", test_smape)
        mlflow.log_metric("val_smape_volume", val_smape_volume)
        mlflow.log_metric("test_smape_volume", test_smape_volume)
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

        quality_pass = archetype_quality_pass and (test_smape_volume <= MAX_SMAPE_THRESHOLD)
        promotion_recommendation = quality_pass and all(gates.values())

        if promotion_block_reason is None and not quality_pass:
            promotion_block_reason = (
                "CRITICAL REJECTION: Overall business-space quality threshold breached. "
                "Forecast error exceeds warehouse operating envelope."
            )
        if has_spiker_warning and promotion_block_reason is None:
            promotion_block_reason = (
                "WARNING: Spiker cohort breached volatility envelope. "
                "Promotion can proceed with caution and floor monitoring."
            )

        if normalized_run_mode == "debug":
            logger.warning("Debug run_mode enabled; promotion recommendation is forced to False.")
            promotion_recommendation = False
            mlflow.log_param("promotion_evidence_allowed", False)
        else:
            mlflow.log_param("promotion_evidence_allowed", True)

        config_snapshot = {
            "MAX_SMAPE_THRESHOLD": MAX_SMAPE_THRESHOLD,
            "REFINERY_EXPECTED_ROW_COUNT": REFINERY_EXPECTED_ROW_COUNT,
            "MAX_ANCHOR_SMAPE": MAX_ANCHOR_SMAPE,
            "MAX_DIAL_SMAPE": MAX_DIAL_SMAPE,
            "MAX_SPIKER_SMAPE": MAX_SPIKER_SMAPE,
            "MAX_PHANTOM_SMAPE": MAX_PHANTOM_SMAPE,
            "ARCHETYPE_HIGH_VOLUME_QUANTILE": ARCHETYPE_HIGH_VOLUME_QUANTILE,
            "ARCHETYPE_LOW_VOLUME_QUANTILE": ARCHETYPE_LOW_VOLUME_QUANTILE,
            "ARCHETYPE_LOW_PREDICTABILITY_QUANTILE": ARCHETYPE_LOW_PREDICTABILITY_QUANTILE,
            "ARCHETYPE_HIGH_PREDICTABILITY_QUANTILE": ARCHETYPE_HIGH_PREDICTABILITY_QUANTILE,
        }

        mlflow.log_param("promotion_gate_metric", "test_smape_volume")
        mlflow.log_param("promotion_gate_threshold", MAX_SMAPE_THRESHOLD)
        mlflow.log_param("quality_pass", quality_pass)
        mlflow.log_param("promotion_recommendation", promotion_recommendation)
        mlflow.log_param("promotion_block_reason", promotion_block_reason or "None")
        mlflow.log_dict(archetype_ledger, artifact_file="reports/archetype_stage3_ledger.json")
        mlflow.log_dict(config_snapshot, artifact_file="reports/config_snapshot.json")

        # STEP 8: Generate and log structured report artifacts for leadership and audit consumption.
        emit_training_run_report(
            run_id=run.info.run_id,
            run_name="xgb_multi_client_ib_uplift",
            cfg=cfg,
            test_smape_target=test_smape,
            val_smape_target=val_smape,
            test_smape_volume=test_smape_volume,
            val_smape_volume=val_smape_volume,
            cmmi_hours_to_baseline=hours_to_baseline,
            cmmi_hours_to_evaluation=hours_to_evaluation,
            cmmi_artifact_completeness=1.0 if gov_record.artifacts_complete else 0.0,
            cmmi_gates=gates,
            promotion_recommendation=promotion_recommendation,
            promotion_gate_metric="test_smape_volume",
            promotion_gate_threshold=MAX_SMAPE_THRESHOLD,
            promotion_gate_value=test_smape_volume,
            promotion_block_reason=promotion_block_reason or "None",
            archetype_stage3_ledger=archetype_ledger,
            config_snapshot=config_snapshot,
            artifact_path="reports",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train XGBoost parcel volume forecast model. "
        "Supports loading from CSV file or Unity Catalog table."
    )
    parser.add_argument(
        "--input-csv",
        required=False,
        default=None,
        help=(
            "Optional CSV file path (e.g. /Workspace/path/data.csv) or "
            "Unity Catalog table name (e.g. catalog.schema.table). "
            "If omitted, source is selected by DEFAULT_INPUT_SOURCE_MODE in src/config.py."
        )
    )
    parser.add_argument(
        "--experiment",
        default=DEFAULT_EXPERIMENT_NAME,
        help="MLflow experiment name or path"
    )
    parser.add_argument(
        "--dataset-version",
        default=DEFAULT_DATASET_VERSION,
        help="Dataset version label for traceability"
    )
    parser.add_argument(
        "--run-mode",
        default="production",
        choices=["production", "debug"],
        help="Execution mode: production (normal) or debug (test)"
    )
    args = parser.parse_args()

    run_training(args.input_csv, args.experiment, args.dataset_version, args.run_mode)
