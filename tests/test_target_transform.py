import numpy as np
import pandas as pd
import pytest

from src.features.target_transform import build_uplift_target, invert_uplift_target

"""Validation tests for the uplift target transform contract.

These tests make the target transformation explicit: the log-uplift target
must be invertible and baseline values must remain strictly positive.
This protects downstream scoring and volume reconstruction semantics.
"""


def test_target_transform_roundtrip():
    df = pd.DataFrame({
        "actual_volume": [100.0, 120.0, 80.0],
        "rolling_4w_median": [100.0, 100.0, 100.0],
    })

    y = build_uplift_target(df)
    # The transform must round-trip exactly for valid baseline values.
    reconstructed = invert_uplift_target(y, df["rolling_4w_median"])

    assert np.allclose(reconstructed.values, df["actual_volume"].values)


def test_build_uplift_target_rejects_non_positive_baseline():
    df = pd.DataFrame({
        "actual_volume": [100.0, 120.0],
        "rolling_4w_median": [100.0, 0.0],
    })

    # The transform contract requires positive baseline values because the
    # log-based uplift formula is undefined at zero or negative baseline.
    with pytest.raises(ValueError, match="must be positive"):
        build_uplift_target(df)


def test_invert_uplift_target_rejects_non_positive_baseline():
    log_uplift = pd.Series([0.0, 0.1])
    baseline = pd.Series([100.0, 0.0])

    # The inverse transform also requires positive baseline values to ensure
    # reconstructed volume remains mathematically valid.
    with pytest.raises(ValueError, match="must be positive"):
        invert_uplift_target(log_uplift, baseline)
