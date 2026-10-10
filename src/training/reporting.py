from __future__ import annotations

"""Training-layer helper for building and logging run report artifacts."""

from src.config import CMMI_MAX_BASELINE_HOURS, CMMI_MAX_EVAL_HOURS, MAX_SMAPE_THRESHOLD
from src.reporting.training_report import build_training_run_report, log_training_run_artifacts_to_mlflow
from src.training.train_config import TrainConfig


def emit_training_run_report(
    *,
    run_id: str,
    run_name: str,
    cfg: TrainConfig,
    test_smape_target: float,
    val_smape_target: float,
    test_smape_volume: float,
    val_smape_volume: float,
    cmmi_hours_to_baseline: float,
    cmmi_hours_to_evaluation: float,
    cmmi_artifact_completeness: float,
    cmmi_gates: dict[str, bool],
    promotion_recommendation: bool,
    promotion_gate_metric: str,
    promotion_gate_threshold: float,
    promotion_gate_value: float,
    promotion_block_reason: str,
    archetype_stage3_ledger: list[dict],
    config_snapshot: dict,
    artifact_path: str = "reports",
) -> None:
    """Build structured report payload and log it as MLflow artifacts."""
    report_payload = build_training_run_report(
        run_id=run_id,
        run_name=run_name,
        dataset_version=cfg.dataset_version,
        model_name=cfg.model_name,
        test_smape_target=test_smape_target,
        val_smape_target=val_smape_target,
        test_smape_volume=test_smape_volume,
        val_smape_volume=val_smape_volume,
        cmmi_hours_to_baseline=cmmi_hours_to_baseline,
        cmmi_hours_to_evaluation=cmmi_hours_to_evaluation,
        cmmi_artifact_completeness=cmmi_artifact_completeness,
        cmmi_gates=cmmi_gates,
        promotion_recommendation=promotion_recommendation,
        promotion_gate_metric=promotion_gate_metric,
        promotion_gate_threshold=promotion_gate_threshold,
        promotion_gate_value=promotion_gate_value,
        promotion_block_reason=promotion_block_reason,
        archetype_stage3_ledger=archetype_stage3_ledger,
        config_snapshot=config_snapshot,
        smape_threshold=MAX_SMAPE_THRESHOLD,
        cmmi_max_baseline_hours=CMMI_MAX_BASELINE_HOURS,
        cmmi_max_eval_hours=CMMI_MAX_EVAL_HOURS,
    )
    log_training_run_artifacts_to_mlflow(report_payload, artifact_path=artifact_path)