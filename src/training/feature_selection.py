from __future__ import annotations

"""Feature-selection helpers for model training."""

import pandas as pd

from src.training.train_config import TrainConfig


def infer_feature_columns(df: pd.DataFrame, cfg: TrainConfig) -> list[str]:
    """Resolve the feature columns used by the training model."""
    if cfg.feature_columns:
        missing = [c for c in cfg.feature_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Configured feature columns are missing from the dataset: {missing}")
        return cfg.feature_columns

    feature_cols = [
        c for c in df.columns
        if c.endswith("_sin") or c.endswith("_cos")
        or c in ["is_china", "is_domestic"]
        or (c.startswith("event_") and c != cfg.date_col)
    ]
    if not feature_cols:
        raise ValueError(
            "Unable to infer feature columns from input data. "
            "Ensure cyclical and business flag columns are present."
        )
    return sorted(feature_cols)