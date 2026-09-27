"""Regression tests for the Stage 2/Stage 3 refinery contract.

These tests protect the training contract from regressions when the source
schema changes or when the live-table volume drifts beyond the approved
guardrail thresholds.
"""

import pandas as pd

from src.training.refinery import (
    RefineryGuardrailResult,
    apply_refinery_filters_to_pandas,
    evaluate_refinery_guardrail,
)


def test_refinery_guardrail_zone_1_passes_nominally():
    result = evaluate_refinery_guardrail(valid_rows=1000, expected_row_count=1000)

    assert result.passed is True
    assert result.failure_reason is None


def test_refinery_guardrail_zone_2_warns_for_approved_deviation():
    result = evaluate_refinery_guardrail(valid_rows=900, expected_row_count=1000)

    assert result.passed is True
    assert result.failure_reason == "WARNING: ApprovedSchemaDeviation"


def test_refinery_guardrail_zone_3_fails_for_data_starvation():
    result = evaluate_refinery_guardrail(valid_rows=400, expected_row_count=1000)

    assert result.passed is False
    assert result.failure_reason == "CRITICAL: DataStarvationError"


def test_apply_refinery_filters_to_pandas_enforces_contract():
    today = pd.Timestamp.today().normalize()
    df = pd.DataFrame(
        {
            "preadvice_date": [today - pd.Timedelta(days=2), today - pd.Timedelta(days=1), None, today - pd.Timedelta(days=400)],
            "parcel_volume": [100.0, None, 200.0, 150.0],
            "median_4wk_volume": [20.0, 15.0, 5.0, 12.0],
            "target": [1.0, 0.5, 0.2, 0.8],
            "china_flag": [0, 1, 0, 1],
            "domestic_flag": [1, 0, 1, 0],
        }
    )

    filtered = apply_refinery_filters_to_pandas(df)

    assert list(filtered.columns) == [
        "event_date",
        "actual_volume",
        "rolling_4w_median",
        "target",
        "is_china",
        "is_domestic",
    ]
    assert len(filtered) == 1
    assert filtered.iloc[0]["event_date"] == today - pd.Timedelta(days=2)
    assert filtered.iloc[0]["rolling_4w_median"] == 20.0
