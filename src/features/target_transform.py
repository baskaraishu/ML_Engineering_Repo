from __future__ import annotations

"""Target transformation helpers for uplift modeling.

Defines forward and inverse transforms between absolute volume and the
log-uplift target used during training/evaluation.
This module captures the transform contract required for consistent
training, validation, and downstream inverse prediction.
"""

import numpy as np
import pandas as pd


def _validate_uplift_target_inputs(
    df: pd.DataFrame,
    actual_col: str,
    baseline_col: str,
) -> None:
    required_columns = {actual_col, baseline_col}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required uplift columns: {sorted(missing_columns)}")

    if df[actual_col].isnull().any():
        raise ValueError(f"Actual volume column '{actual_col}' contains null values.")
    if df[baseline_col].isnull().any():
        raise ValueError(f"Baseline column '{baseline_col}' contains null values.")

    if (df[baseline_col] <= 0).any():
        raise ValueError(f"Baseline values in '{baseline_col}' must be positive.")
    if (df[actual_col] < 0).any():
        raise ValueError(f"Actual volume values in '{actual_col}' must be non-negative.")


def build_uplift_target(
    df: pd.DataFrame,
    actual_col: str = "actual_volume",
    baseline_col: str = "rolling_4w_median",
    clip_floor: float = 1e-6,
) -> pd.Series:
    """Create log-uplift target: log(actual / baseline)."""
    _validate_uplift_target_inputs(df, actual_col, baseline_col)
    ratio = (df[actual_col] / df[baseline_col]).clip(lower=clip_floor)
    return np.log(ratio)


def invert_uplift_target(log_uplift: pd.Series, baseline: pd.Series) -> pd.Series:
    """Invert log-uplift back to predicted absolute volume."""
    baseline_series = pd.Series(baseline).astype(float)
    if baseline_series.isnull().any():
        raise ValueError("Baseline series contains null values.")
    if (baseline_series <= 0).any():
        raise ValueError("Baseline values must be positive for inverse transform.")
    return np.exp(log_uplift) * baseline_series
