from __future__ import annotations

"""Input-data validation helpers for the training pipeline."""

import pandas as pd

from src.training.train_config import TrainConfig


def validate_input_dataframe(df: pd.DataFrame, cfg: TrainConfig) -> None:
    """Validate the required columns and value constraints for training input."""
    missing_columns = [c for c in [cfg.date_col, cfg.actual_col, cfg.baseline_col] if c not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required training columns: {missing_columns}")

    if df[[cfg.date_col, cfg.actual_col, cfg.baseline_col]].isnull().any().any():
        raise ValueError("Input dataset contains null values in required training columns.")

    if (df[cfg.actual_col] < 0).any():
        raise ValueError(f"Actual volume column '{cfg.actual_col}' contains negative values.")

    if (df[cfg.baseline_col] <= 0).any():
        raise ValueError(f"Baseline column '{cfg.baseline_col}' must contain only positive values.")