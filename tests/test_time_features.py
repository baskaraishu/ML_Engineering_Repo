"""Unit tests for cyclical time feature engineering.

These tests validate the contract for add_cyclical_time_features():
- All expected sin/cos columns are produced.
- Values are within the valid cyclical range [-1.0, 1.0].
- sin and cos encode periodicity correctly for known calendar dates.
- No NaN values appear in the output.
- The original input columns are preserved (non-destructive transform).
- The function is deterministic: same input always produces the same output.

The cyclical encoding contract is:
  sin = sin(2π × value / period)
  cos = cos(2π × value / period)

For example, January (month=1, period=12):
  month_sin = sin(2π × 1 / 12) ≈ 0.5
  month_cos = cos(2π × 1 / 12) ≈ 0.866
"""

import numpy as np
import pandas as pd
import pytest

from src.features.time_features import add_cyclical_time_features


EXPECTED_CYCLICAL_COLUMNS = [
    "month_sin", "month_cos",
    "dow_sin",   "dow_cos",
    "doy_sin",   "doy_cos",
    "woy_sin",   "woy_cos",
    "dom_sin",   "dom_cos",
]


def _make_df(dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"event_date": pd.to_datetime(dates), "value": 1.0})


def test_all_expected_columns_produced():
    """All ten cyclical columns must be present in the output."""
    df = _make_df(["2026-01-01"])
    out = add_cyclical_time_features(df, "event_date")
    for col in EXPECTED_CYCLICAL_COLUMNS:
        assert col in out.columns, f"Expected column '{col}' not found in output."


def test_cyclical_values_in_valid_range():
    """All sin/cos values must lie within [-1.0, 1.0] — the valid cyclical range."""
    df = _make_df(pd.date_range("2026-01-01", periods=365, freq="D").strftime("%Y-%m-%d").tolist())
    out = add_cyclical_time_features(df, "event_date")
    for col in EXPECTED_CYCLICAL_COLUMNS:
        assert out[col].between(-1.0, 1.0).all(), f"Column '{col}' contains values outside [-1, 1]."


def test_no_nulls_in_output():
    """No NaN values should appear in any cyclical output column."""
    df = _make_df(["2026-01-01", "2026-06-15", "2026-12-31"])
    out = add_cyclical_time_features(df, "event_date")
    for col in EXPECTED_CYCLICAL_COLUMNS:
        assert not out[col].isnull().any(), f"Column '{col}' contains NaN values."


def test_original_columns_preserved():
    """The transform must not remove the original input columns."""
    df = _make_df(["2026-01-01"])
    out = add_cyclical_time_features(df, "event_date")
    assert "event_date" in out.columns
    assert "value" in out.columns


def test_deterministic_output():
    """Calling the function twice on the same input must produce identical results."""
    df = _make_df(["2026-03-15", "2026-09-01"])
    out1 = add_cyclical_time_features(df, "event_date")
    out2 = add_cyclical_time_features(df, "event_date")
    for col in EXPECTED_CYCLICAL_COLUMNS:
        pd.testing.assert_series_equal(out1[col], out2[col])


def test_month_sin_cos_january():
    """January (month=1, period=12) should produce known sin/cos values."""
    df = _make_df(["2026-01-15"])
    out = add_cyclical_time_features(df, "event_date")
    expected_sin = np.sin(2 * np.pi * 1 / 12)
    expected_cos = np.cos(2 * np.pi * 1 / 12)
    assert out["month_sin"].iloc[0] == pytest.approx(expected_sin, abs=1e-9)
    assert out["month_cos"].iloc[0] == pytest.approx(expected_cos, abs=1e-9)


def test_dow_sin_cos_monday():
    """Monday (dayofweek=0, period=7) should produce sin=0 and cos=1."""
    # 2026-06-22 is a Monday
    df = _make_df(["2026-06-22"])
    out = add_cyclical_time_features(df, "event_date")
    expected_sin = np.sin(2 * np.pi * 0 / 7)
    expected_cos = np.cos(2 * np.pi * 0 / 7)
    assert out["dow_sin"].iloc[0] == pytest.approx(expected_sin, abs=1e-9)
    assert out["dow_cos"].iloc[0] == pytest.approx(expected_cos, abs=1e-9)


def test_input_dataframe_not_mutated():
    """The original DataFrame must not be modified in place."""
    df = _make_df(["2026-01-01"])
    original_columns = list(df.columns)
    add_cyclical_time_features(df, "event_date")
    assert list(df.columns) == original_columns
