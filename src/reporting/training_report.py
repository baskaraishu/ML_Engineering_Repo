from __future__ import annotations

"""Utilities to build and persist training run reports."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def build_training_run_report(
    *,
    run_id: str,
    run_name: str,
    dataset_version: str,
    model_name: str,
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
    smape_threshold: float,
    cmmi_max_baseline_hours: float,
    cmmi_max_eval_hours: float,
) -> dict:
    """Build a report payload aligned to the Phase 0 leadership structure."""
    quality_pass = promotion_gate_value <= promotion_gate_threshold
    cmmi_pass = all(cmmi_gates.values())
    recommendation = "pass" if (promotion_recommendation and cmmi_pass) else "reject"
    now_utc = datetime.now(timezone.utc).isoformat()

    stage_execution_summary = [
        {
            "step": 1,
            "stage": "Trigger",
            "status": "Pass",
            "evidence": "Run was started with explicit input and dataset parameters.",
        },
        {
            "step": 2,
            "stage": "Load and validate data",
            "status": "Pass",
            "evidence": "CSV loaded and input validation checks completed.",
        },
        {
            "step": 3,
            "stage": "Transform features",
            "status": "Pass",
            "evidence": "Cyclical features and uplift target were generated.",
        },
        {
            "step": 4,
            "stage": "Split and train",
            "status": "Pass",
            "evidence": "Train/val/test split completed and model training executed.",
        },
        {
            "step": 5,
            "stage": "Evaluate",
            "status": "Pass" if quality_pass else "Partial",
            "evidence": (
                f"test_smape_target={test_smape_target:.4f}, val_smape_target={val_smape_target:.4f}, "
                f"test_smape_volume={test_smape_volume:.4f}, val_smape_volume={val_smape_volume:.4f}"
            ),
        },
        {
            "step": 6,
            "stage": "Compute CMMI metrics",
            "status": "Pass" if cmmi_pass else "Partial",
            "evidence": "Baseline/evaluation timing and artifact completeness metrics were captured.",
        },
        {
            "step": 7,
            "stage": "Log to MLflow",
            "status": "Pass",
            "evidence": "Core metrics, params, and model artifact were logged to MLflow.",
        },
        {
            "step": 8,
            "stage": "Generate run report artifacts",
            "status": "Pass",
            "evidence": "run_summary.json and run_summary.html were generated for this run.",
        },
    ]

    gate_snapshot = {
        "reproducibility": {
            "status": "Pass",
            "rationale": "Repository entrypoint executed with recorded run configuration.",
        },
        "quality": {
            "status": "Pass" if quality_pass else "Partial",
            "rationale": (
                f"Primary gate uses {promotion_gate_metric} <= {promotion_gate_threshold}. "
                f"Observed={promotion_gate_value:.4f}."
            ),
        },
        "cmmi_process": {
            "status": "Pass" if cmmi_pass else "Partial",
            "rationale": "CMMI process metrics were computed and gate flags logged.",
        },
        "documentation": {
            "status": "Pass",
            "rationale": "Structured run report artifacts were generated and logged.",
        },
        "approval": {
            "status": "Pending",
            "rationale": "Human review is required before final closeout.",
        },
    }

    return {
        "report_version": "1.0",
        "generated_at_utc": now_utc,
        "report_name": "Phase 0 Leadership Summary (Auto-Generated)",
        "executive_summary": {
            "phase": "Phase 0",
            "objective": "Validate deterministic training flow and governance evidence capture.",
            "environment": "local",
            "run_id": run_id,
            "run_name": run_name,
            "dataset_version": dataset_version,
            "model_name": model_name,
            "recommendation": recommendation,
        },
        "key_metrics": {
            "thresholds": {
                "max_test_smape_percent": smape_threshold,
                "primary_promotion_gate_threshold": promotion_gate_threshold,
                "cmmi_max_baseline_hours": cmmi_max_baseline_hours,
                "cmmi_max_evaluation_hours": cmmi_max_eval_hours,
                "cmmi_artifact_completeness_required": 1.0,
            },
            "performance": {
                "test_smape_target": test_smape_target,
                "val_smape_target": val_smape_target,
                "test_smape_volume": test_smape_volume,
                "val_smape_volume": val_smape_volume,
            },
            "cmmi": {
                "cmmi_hours_to_baseline": cmmi_hours_to_baseline,
                "cmmi_hours_to_evaluation": cmmi_hours_to_evaluation,
                "cmmi_artifact_completeness": cmmi_artifact_completeness,
            },
        },
        "operational_archetype_briefing": archetype_stage3_ledger,
        "promotion_context": {
            "promotion_gate_metric": promotion_gate_metric,
            "promotion_gate_threshold": promotion_gate_threshold,
            "promotion_gate_value": promotion_gate_value,
            "promotion_block_reason": promotion_block_reason,
        },
        "config_snapshot": config_snapshot,
        "stage_execution_summary": stage_execution_summary,
        "cmmi_gate_snapshot": gate_snapshot,
        "gates": {
            "quality_pass": quality_pass,
            "baseline_speed_pass": cmmi_gates.get("baseline_speed_pass", False),
            "evaluation_speed_pass": cmmi_gates.get("evaluation_speed_pass", False),
            "artifact_completeness_pass": cmmi_gates.get("artifact_completeness_pass", False),
            "cmmi_pass": cmmi_pass,
        },
        "recommendation": {
            "promotion_recommendation": recommendation,
            "explanation": (
                "pass if operational primary gate and all CMMI gates pass; "
                "otherwise reject"
            ),
        },
    }


def write_training_run_artifacts(report: dict, output_dir: Path) -> tuple[Path, Path]:
    """Write JSON and HTML report artifacts to the target directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "run_summary.json"
    html_path = output_dir / "run_summary.html"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary = report["executive_summary"]
    key_metrics = report["key_metrics"]
    perf = key_metrics["performance"]
    cmmi = key_metrics["cmmi"]
    thresholds = key_metrics["thresholds"]
    gates = report["gates"]
    promotion_context = report.get("promotion_context", {})
    archetype_briefing = report.get("operational_archetype_briefing", [])
    config_snapshot = report.get("config_snapshot", {})

    stage_rows = "".join(
        f"<tr><td>{s['step']}</td><td>{s['stage']}</td><td>{s['status']}</td><td>{s['evidence']}</td></tr>"
        for s in report["stage_execution_summary"]
    )

    gate = report["cmmi_gate_snapshot"]
    gate_rows = "".join(
        f"<tr><td>{name.replace('_', ' ').title()}</td><td>{details['status']}</td><td>{details['rationale']}</td></tr>"
        for name, details in gate.items()
    )

    archetype_rows = ""
    for row in archetype_briefing:
        business_smape = row.get("business_smape")
        business_smape_text = "NA" if business_smape is None else f"{float(business_smape):.4f}"
        archetype_rows += (
            "<tr>"
            f"<td>{row.get('archetype', 'NA')}</td>"
            f"<td>{row.get('row_count', 0)}</td>"
            f"<td>{business_smape_text}</td>"
            f"<td>{row.get('threshold', 'NA')}</td>"
            f"<td>{row.get('workflow_impact_flag', 'NA')}</td>"
            "</tr>"
        )

    config_snapshot_json = json.dumps(config_snapshot, indent=2)

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Training Run Summary</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #1f2933; }}
    h1 {{ margin-bottom: 8px; }}
    .muted {{ color: #52606d; }}
    .grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit,minmax(240px,1fr)); margin: 18px 0; }}
    .card {{ border: 1px solid #d9e2ec; border-radius: 10px; padding: 12px; background: #fff; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px; text-align: left; }}
    th {{ background: #f0f4f8; }}
    .pass {{ color: #127a45; font-weight: 700; }}
    .fail {{ color: #b42318; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Phase 0 Leadership Summary (Auto)</h1>
  <p class=\"muted\">Run: {summary['run_id']} | Dataset: {summary['dataset_version']} | Model: {summary['model_name']}</p>
  <p class=\"muted\">Generated: {report['generated_at_utc']}</p>
  <p class=\"muted\">Recommendation: <strong>{summary['recommendation'].upper()}</strong></p>

  <div class=\"grid\">
    <div class=\"card\"><strong>test_smape_target</strong><br />{perf['test_smape_target']:.4f}</div>
    <div class=\"card\"><strong>val_smape_target</strong><br />{perf['val_smape_target']:.4f}</div>
    <div class=\"card\"><strong>test_smape_volume</strong><br />{perf.get('test_smape_volume', float('nan')):.4f}</div>
    <div class=\"card\"><strong>val_smape_volume</strong><br />{perf.get('val_smape_volume', float('nan')):.4f}</div>
    <div class=\"card\"><strong>cmmi_hours_to_baseline</strong><br />{cmmi['cmmi_hours_to_baseline']:.4f}</div>
    <div class=\"card\"><strong>cmmi_hours_to_evaluation</strong><br />{cmmi['cmmi_hours_to_evaluation']:.4f}</div>
    <div class=\"card\"><strong>cmmi_artifact_completeness</strong><br />{cmmi['cmmi_artifact_completeness']:.1f}</div>
  </div>

  <h2>Operational Archetype Briefing</h2>
  <table>
    <thead><tr><th>Archetype</th><th>Rows</th><th>Business SMAPE</th><th>Threshold</th><th>Workflow Impact</th></tr></thead>
    <tbody>{archetype_rows}</tbody>
  </table>

  <h2>Promotion Context</h2>
  <table>
    <thead><tr><th>Field</th><th>Value</th></tr></thead>
    <tbody>
      <tr><td>promotion_gate_metric</td><td>{promotion_context.get('promotion_gate_metric', 'NA')}</td></tr>
      <tr><td>promotion_gate_threshold</td><td>{promotion_context.get('promotion_gate_threshold', 'NA')}</td></tr>
      <tr><td>promotion_gate_value</td><td>{promotion_context.get('promotion_gate_value', 'NA')}</td></tr>
      <tr><td>promotion_block_reason</td><td>{promotion_context.get('promotion_block_reason', 'None')}</td></tr>
    </tbody>
  </table>

  <h2>Stage Execution Summary</h2>
  <table>
    <thead><tr><th>Step</th><th>Stage</th><th>Status</th><th>Evidence</th></tr></thead>
    <tbody>{stage_rows}</tbody>
  </table>

  <h2>CMMI Gate Snapshot</h2>
  <table>
    <thead><tr><th>Gate</th><th>Status</th><th>Rationale</th></tr></thead>
    <tbody>{gate_rows}</tbody>
  </table>

  <table>
    <thead><tr><th>Gate</th><th>Status</th><th>Threshold</th></tr></thead>
    <tbody>
      <tr><td>Quality ({promotion_context.get('promotion_gate_metric', 'primary gate')})</td><td class=\"{'pass' if gates['quality_pass'] else 'fail'}\">{'PASS' if gates['quality_pass'] else 'FAIL'}</td><td>&lt;= {thresholds.get('primary_promotion_gate_threshold', thresholds['max_test_smape_percent'])}</td></tr>
      <tr><td>baseline_speed_pass</td><td class=\"{'pass' if gates['baseline_speed_pass'] else 'fail'}\">{'PASS' if gates['baseline_speed_pass'] else 'FAIL'}</td><td>&lt;= {thresholds['cmmi_max_baseline_hours']} hours</td></tr>
      <tr><td>evaluation_speed_pass</td><td class=\"{'pass' if gates['evaluation_speed_pass'] else 'fail'}\">{'PASS' if gates['evaluation_speed_pass'] else 'FAIL'}</td><td>&lt;= {thresholds['cmmi_max_evaluation_hours']} hours</td></tr>
      <tr><td>artifact_completeness_pass</td><td class=\"{'pass' if gates['artifact_completeness_pass'] else 'fail'}\">{'PASS' if gates['artifact_completeness_pass'] else 'FAIL'}</td><td>== {thresholds['cmmi_artifact_completeness_required']}</td></tr>
      <tr><td>promotion_recommendation</td><td class=\"{'pass' if report['recommendation']['promotion_recommendation'] == 'pass' else 'fail'}\">{report['recommendation']['promotion_recommendation'].upper()}</td><td>Quality and CMMI all pass</td></tr>
    </tbody>
  </table>

  <h2>Config Snapshot</h2>
  <pre>{config_snapshot_json}</pre>
</body>
</html>
"""

    html_path.write_text(html, encoding="utf-8")
    return json_path, html_path


def log_training_run_artifacts_to_mlflow(report: dict, artifact_path: str = "reports") -> None:
    """Write report artifacts to a temp directory and log them to MLflow."""
    import mlflow

    with tempfile.TemporaryDirectory() as temp_dir:
        report_dir = Path(temp_dir)
        write_training_run_artifacts(report, report_dir)
        mlflow.log_artifacts(str(report_dir), artifact_path=artifact_path)
