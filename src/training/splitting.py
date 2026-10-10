from __future__ import annotations

"""Time-based dataset splitting helpers for model training."""

import pandas as pd


def split_train_val_test(df: pd.DataFrame, date_col: str, test_days: int, val_days: int):
    """Split the dataset into contiguous train, validation, and test windows."""
    ordered = df.sort_values(date_col).copy()
    max_date = ordered[date_col].max()
    if pd.isna(max_date):
        raise ValueError(f"Date column '{date_col}' contains no valid values.")

    test_days_int = int(test_days)
    val_days_int = int(val_days)
    test_start = max_date - pd.to_timedelta(test_days_int - 1, unit="days")
    val_start = test_start - pd.to_timedelta(val_days_int, unit="days")

    train = ordered[ordered[date_col] < val_start]
    val = ordered[(ordered[date_col] >= val_start) & (ordered[date_col] < test_start)]
    test = ordered[ordered[date_col] >= test_start]

    if train.empty or val.empty or test.empty:
        raise ValueError(
            "Insufficient data for time-based train/validation/test split. "
            f"Train={len(train)}, val={len(val)}, test={len(test)}. "
            "Verify input data spans the expected date range."
        )

    return train, val, test