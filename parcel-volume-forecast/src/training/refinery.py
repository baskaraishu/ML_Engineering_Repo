from __future__ import annotations

"""Config-driven data refinery helpers for the Stage 2 and Stage 3 training contract.

Use this module when the training source is a live table or another large,
noisy dataset. It keeps the Spark-side filtering and the governance guardrail
explicit so the training pipeline can fail fast on bad data quality rather
than silently training on an invalid slice.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from src.config import (
    ACTUAL_COL,
    BASELINE_COL,
    DATE_COL,
    MIN_CLIENT_MEDIAN_VOLUME,
    REFINERY_EXPECTED_ROW_COUNT,
    REFINERY_MAX_DROP_FRACTION,
    REFINERY_MIN_ROW_FRACTION,
    REFINERY_NOMINAL_DROP_FRAC,
    TARGET_COL,
    TRAINING_LOOKBACK_DAYS,
)


@dataclass(frozen=True)
class RefineryGuardrailResult:
    """Represents the outcome of the three-zone volumetric guardrail."""

    passed: bool
    failure_reason: str | None
    drop_frac: float
    valid_rows: int
    expected_row_count: int


def _get_refinery_manifest() -> dict[str, Any]:
    return {
        "column_map": {
            "date": {"source": "preadvice_date", "target": DATE_COL},
            "volume": {"source": "parcel_volume", "target": ACTUAL_COL},
            "baseline": {"source": "median_4wk_volume", "target": BASELINE_COL},
            "target": {"source": TARGET_COL, "target": TARGET_COL},
            "china": {"source": "china_flag", "target": "is_china"},
            "domestic": {"source": "domestic_flag", "target": "is_domestic"},
        },
        "push_down_filters": {
            "lookback_days": TRAINING_LOOKBACK_DAYS,
            "min_baseline_volume": MIN_CLIENT_MEDIAN_VOLUME,
            "require_non_null": ["preadvice_date", "parcel_volume", "median_4wk_volume", TARGET_COL],
        },
        "guardrail": {
            "expected_row_count": REFINERY_EXPECTED_ROW_COUNT,
            "min_row_fraction": REFINERY_MIN_ROW_FRACTION,
            "max_drop_fraction": REFINERY_MAX_DROP_FRACTION,
            "nominal_drop_frac": REFINERY_NOMINAL_DROP_FRAC,
        },
    }


def apply_refinery_filters_to_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the Stage 2 contract to a pandas frame.

    The contract mirrors the planned Spark SQL enforcement: project only the
    required columns, enforce temporal and cohort filters, and require a non-null
    target before any data is accepted into the training slice.
    """

    manifest = _get_refinery_manifest()
    column_map = manifest["column_map"]
    filters = manifest["push_down_filters"]
    required_columns = {
        column_map["date"]["source"],
        column_map["volume"]["source"],
        column_map["baseline"]["source"],
        column_map["target"]["source"],
        column_map["china"]["source"],
        column_map["domestic"]["source"],
    }

    available_columns = set(df.columns)
    missing_columns = required_columns - available_columns
    if missing_columns:
        raise ValueError(f"Missing required refinery columns: {sorted(missing_columns)}")

    candidate = df.loc[:, list(required_columns)].copy()
    candidate[DATE_COL] = pd.to_datetime(candidate[column_map["date"]["source"]], errors="coerce")
    candidate[ACTUAL_COL] = pd.to_numeric(candidate[column_map["volume"]["source"]], errors="coerce")
    candidate[BASELINE_COL] = pd.to_numeric(candidate[column_map["baseline"]["source"]], errors="coerce")
    candidate[TARGET_COL] = pd.to_numeric(candidate[column_map["target"]["source"]], errors="coerce")
    candidate["is_china"] = pd.to_numeric(candidate[column_map["china"]["source"]], errors="coerce")
    candidate["is_domestic"] = pd.to_numeric(candidate[column_map["domestic"]["source"]], errors="coerce")

    cutoff = datetime.now().date() - timedelta(days=filters["lookback_days"])
    filtered = candidate[
        (candidate[DATE_COL].notna())
        & (candidate[ACTUAL_COL].notna())
        & (candidate[BASELINE_COL].notna())
        & (candidate[TARGET_COL].notna())
        & (candidate[BASELINE_COL] > filters["min_baseline_volume"])
        & (candidate[DATE_COL] >= pd.Timestamp(cutoff))
    ].copy()

    filtered = filtered.rename(
        columns={
            DATE_COL: DATE_COL,
            ACTUAL_COL: ACTUAL_COL,
            BASELINE_COL: BASELINE_COL,
            TARGET_COL: TARGET_COL,
            "is_china": "is_china",
            "is_domestic": "is_domestic",
        }
    )

    return filtered[[DATE_COL, ACTUAL_COL, BASELINE_COL, TARGET_COL, "is_china", "is_domestic"]]


def evaluate_refinery_guardrail(valid_rows: int, expected_row_count: int) -> RefineryGuardrailResult:
    """Evaluate the Stage 3 volumetric compliance envelope."""

    manifest = _get_refinery_manifest()
    guardrail = manifest["guardrail"]
    drop_frac = 1 - (valid_rows / expected_row_count) if expected_row_count else 1.0

    if valid_rows < expected_row_count * guardrail["min_row_fraction"]:
        return RefineryGuardrailResult(
            passed=False,
            failure_reason="CRITICAL: DataStarvationError",
            drop_frac=drop_frac,
            valid_rows=valid_rows,
            expected_row_count=expected_row_count,
        )

    if drop_frac > guardrail["max_drop_fraction"]:
        return RefineryGuardrailResult(
            passed=False,
            failure_reason="CRITICAL: DataQualityError",
            drop_frac=drop_frac,
            valid_rows=valid_rows,
            expected_row_count=expected_row_count,
        )

    if drop_frac <= guardrail["nominal_drop_frac"]:
        return RefineryGuardrailResult(
            passed=True,
            failure_reason=None,
            drop_frac=drop_frac,
            valid_rows=valid_rows,
            expected_row_count=expected_row_count,
        )

    return RefineryGuardrailResult(
        passed=True,
        failure_reason="WARNING: ApprovedSchemaDeviation",
        drop_frac=drop_frac,
        valid_rows=valid_rows,
        expected_row_count=expected_row_count,
    )
