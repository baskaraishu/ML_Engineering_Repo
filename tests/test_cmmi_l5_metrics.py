from datetime import datetime, timedelta

from src.governance.cmmi_l5_metrics import (
    CmmiRunRecord,
    cmmi_l5_gate_status,
    promotion_rate,
)

"""Tests for CMMI Level 5 governance metric mechanics.

This module validates the core CMMI process metric logic that the repo
uses to determine whether a training run meets defined process gates.
The record objects and gate calculations are intended to track:
- how quickly the run reached baseline readiness,
- how quickly evaluation completed,
- whether required artifacts were produced,
- and whether the run is eligible for promotion.

These tests enforce the governance contract in code, not just in
manual review documentation.
"""


def test_cmmi_gate_status_and_promotion_rate():
    start = datetime(2026, 6, 1, 9, 0, 0)

    r1 = CmmiRunRecord(
        run_id="r1",
        model_name="xgb_ib_uplift",
        dataset_version="v1",
        experiment_start=start,
        baseline_ready=start + timedelta(hours=1),
        evaluation_complete=start + timedelta(hours=8),
        promoted=True,
        artifacts_complete=True,
    )
    r2 = CmmiRunRecord(
        run_id="r2",
        model_name="xgb_ib_uplift",
        dataset_version="v1",
        experiment_start=start,
        baseline_ready=start + timedelta(hours=3),
        evaluation_complete=start + timedelta(hours=30),
        promoted=False,
        artifacts_complete=False,
    )

    # Evaluate the first run against the defined CMMI L5 process gates.
    # The default thresholds in `cmmi_l5_gate_status()` are:
    # - baseline speed must complete within 2.0 hours
    # - evaluation speed must complete within 24.0 hours
    # - artifact completeness must be True
    gates = cmmi_l5_gate_status(r1)
    assert gates["baseline_speed_pass"] is True
    assert gates["evaluation_speed_pass"] is True
    assert gates["artifact_completeness_pass"] is True

    # Promotion rate is a simple governance indicator: the fraction of runs
    # that were marked as promoted among the evaluated run set.
    assert promotion_rate([r1, r2]) == 0.5
