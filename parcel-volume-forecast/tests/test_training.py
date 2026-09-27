import pandas as pd
import pytest

from src.training.data_validation import validate_input_dataframe
from src.training.feature_selection import infer_feature_columns
from src.training.splitting import split_train_val_test
from src.training.train_xgboost import TrainConfig

"""Validation tests for training helpers and time-based split logic.

These tests document the repository's training contract for feature inference,
input validation, and train/validation/test partitioning. They encode the
expected behavior of the training pipeline so changes are caught early.
"""


def test_infer_feature_columns_default():
    df = pd.DataFrame({
        "month_sin": [0.0],
        "month_cos": [1.0],
        "dow_sin": [0.0],
        "dow_cos": [1.0],
        "is_china": [1],
    })
    cfg = TrainConfig()

    # The feature inference contract is based on expected cyclical and flag
    # column patterns. This ensures the training code uses only designated
    # feature columns when explicit columns are not provided.
    features = infer_feature_columns(df, cfg)

    assert sorted(features) == ["dow_cos", "dow_sin", "is_china", "month_cos", "month_sin"]


def test_infer_feature_columns_explicit():
    df = pd.DataFrame({"x": [1], "y": [2]})
    cfg = TrainConfig(feature_columns=["x", "y"])

    features = infer_feature_columns(df, cfg)

    assert features == ["x", "y"]


def test_infer_feature_columns_missing_explicit():
    df = pd.DataFrame({"x": [1]})
    cfg = TrainConfig(feature_columns=["x", "y"])

    with pytest.raises(ValueError, match="Configured feature columns are missing"):
        infer_feature_columns(df, cfg)


def test_validate_input_dataframe_rejects_bad_values():
    df = pd.DataFrame(
        {
            "event_date": ["2026-06-01", "2026-06-02"],
            "actual_volume": [100.0, -1.0],
            "rolling_4w_median": [100.0, 100.0],
        }
    )
    cfg = TrainConfig()

    # Input validation is a hard gating step for training. Negative actual
    # volume values are rejected because the uplift target assumes positive
    # business volume semantics.
    with pytest.raises(ValueError, match="contains negative values"):
        validate_input_dataframe(df, cfg)


def test_split_train_val_test_success():
    df = pd.DataFrame(
        {
            "event_date": pd.date_range(start="2026-01-01", periods=100, freq="D"),
            "actual_volume": [100.0] * 100,
            "rolling_4w_median": [90.0] * 100,
        }
    )
    train, val, test = split_train_val_test(df, "event_date", test_days=14, val_days=14)

    # The time-window split contract uses contiguous calendar windows, with
    # 14 days reserved for validation and 14 days reserved for test.
    assert len(train) == 72
    assert len(val) == 14
    assert len(test) == 14


def test_split_train_val_test_failure_insufficient_data():
    df = pd.DataFrame(
        {
            "event_date": pd.date_range(start="2026-01-01", periods=20, freq="D"),
            "actual_volume": [100.0] * 20,
            "rolling_4w_median": [90.0] * 20,
        }
    )

    with pytest.raises(ValueError, match="Insufficient data for time-based train/validation/test split"):
        split_train_val_test(df, "event_date", test_days=14, val_days=14)
