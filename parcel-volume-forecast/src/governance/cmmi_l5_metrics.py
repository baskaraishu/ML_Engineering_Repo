from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.config import CMMI_MAX_BASELINE_HOURS, CMMI_MAX_EVAL_HOURS

"""CMMI Level 5 process metrics used for run-level gate decisions.

This module focuses on process discipline metrics rather than model-quality metrics.
Training and reporting layers consume these functions to compute reproducibility and
artifact-readiness evidence for phase closeout reviews.
"""


@dataclass
class CmmiRunRecord:
    run_id: str
    model_name: str
    dataset_version: str
    experiment_start: datetime
    baseline_ready: datetime
    evaluation_complete: datetime
    promoted: bool
    artifacts_complete: bool
    drift_detected_at: datetime | None = None


def hours_to_baseline(record: CmmiRunRecord) -> float:
    """CMMI metric: time from experiment start to first baseline."""
    return (record.baseline_ready - record.experiment_start).total_seconds() / 3600.0


def hours_to_evaluation(record: CmmiRunRecord) -> float:
    """CMMI metric: time to complete full evaluation artifacts."""
    return (record.evaluation_complete - record.experiment_start).total_seconds() / 3600.0


def evaluation_artifact_completeness(record: CmmiRunRecord) -> float:
    """CMMI metric: binary completeness score for required artifacts."""
    return 1.0 if record.artifacts_complete else 0.0


def promotion_rate(records: list[CmmiRunRecord]) -> float:
    """CMMI metric: ratio of promoted models to total evaluated runs."""
    if not records:
        return 0.0
    promoted = sum(1 for r in records if r.promoted)
    return promoted / len(records)


def drift_detection_latency_hours(record: CmmiRunRecord, prediction_shift_start: datetime) -> float | None:
    """CMMI metric: lag between drift onset and detection alert time."""
    if record.drift_detected_at is None:
        return None
    return (record.drift_detected_at - prediction_shift_start).total_seconds() / 3600.0


def cmmi_l5_gate_status(record: CmmiRunRecord, max_baseline_hours: float = CMMI_MAX_BASELINE_HOURS, max_eval_hours: float = CMMI_MAX_EVAL_HOURS) -> dict[str, bool]:
    """Return pass/fail flags for core CMMI L5 process gates."""
    return {
        "baseline_speed_pass": hours_to_baseline(record) <= max_baseline_hours,
        "evaluation_speed_pass": hours_to_evaluation(record) <= max_eval_hours,
        "artifact_completeness_pass": evaluation_artifact_completeness(record) == 1.0,
    }
