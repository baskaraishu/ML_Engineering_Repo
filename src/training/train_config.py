from __future__ import annotations

"""Configuration object for the training pipeline."""

from dataclasses import dataclass

from src.config import (
    ACTUAL_COL,
    BASELINE_COL,
    DATE_COL,
    DEFAULT_DATASET_VERSION,
    MODEL_NAME,
    TARGET_COL,
    TEST_DAYS,
    VAL_DAYS,
)


@dataclass
class TrainConfig:
    """Training configuration for the XGBoost uplift forecast run."""

    date_col: str = DATE_COL
    actual_col: str = ACTUAL_COL
    baseline_col: str = BASELINE_COL
    target_col: str = TARGET_COL
    test_days: int = TEST_DAYS
    val_days: int = VAL_DAYS
    dataset_version: str = DEFAULT_DATASET_VERSION
    model_name: str = MODEL_NAME
    feature_columns: list[str] | None = None