# Repository Structure and CMMI L5 Guide

## Purpose
This guide explains why each major folder and key file exists, what team problem it solves, and which CMMI Level 5 control objective it supports.

## Folder Intent and CMMI Mapping

| Path | Why it exists | Team outcome | CMMI L5 linkage | Primary evidence |
|---|---|---|---|---|
| `notebooks/` | Keep fast exploration and Genie-assisted diagnostics separate from production logic | Faster ideation without polluting deployable code | Controlled lifecycle separation | Notebook analyses, exploratory outputs |
| `src/data/` | Centralize reusable training-data loading and validation logic | Repeatable, testable input preparation | Quantitative management readiness | `src/data/load_training_data.py` |
| `src/features/` | Reusable feature and target transforms | Consistent feature behavior across runs | Defect prevention | `src/features/time_features.py`, `src/features/target_transform.py` |
| `src/training/` | Deterministic training entrypoints and run logging | Reproducible model build process | Quantitative project management | `src/training/train_xgboost.py` |
| `src/evaluation/` | Standard metric definitions | Comparable model-quality decisions | Statistical performance control | `src/evaluation/metrics.py` |
| `src/governance/` | Process KPI and gate logic | Measurable process discipline | Causal analysis and process performance | `src/governance/cmmi_l5_metrics.py` |
| `jobs/` | Workflow orchestration definitions | Scheduled, auditable operations | Managed process execution | `jobs/train_job.yaml` |
| `sql/` | Governed KPI and serving views | Shared metric truth and reporting consistency | Organizational process performance | `sql/cmmi_l5_process_metrics.sql`, `sql/serving_forecast_view.sql` |
| `tests/` | Regression and unit protection | Safe change velocity | Defect prevention and stability | `tests/test_target_transform.py`, `tests/test_cmmi_l5_metrics.py` |
| `docs/project/` | Operational runbook and decisions | Traceable go/no-go history | Institutional learning and governance | `docs/project/runbook.md`, `docs/project/decision_log.md` |
| `docs/ai-governance/` | Model governance artifacts | Audit-ready model context | Governance compliance | model card, risk, and lineage docs |
| `workflow/requirements/` | Approved scope contracts before implementation | Requirements-first delivery discipline | CMMI Gate 0 enforcement | approved requirement files |

## Key File Intent

| File | Why it exists | When to update |
|---|---|---|
| `src/training/train_xgboost.py` | Main Phase 1 training flow with MLflow and CMMI metric capture | Any training logic or run-metric change |
| `src/governance/cmmi_l5_metrics.py` | Core CMMI process metric calculations and gate evaluation | Any change to gate thresholds or process KPIs |
| `sql/cmmi_l5_process_metrics.sql` | Aggregated process KPI reporting view | Any change to process KPI definitions or reporting granularity |
| `jobs/train_job.yaml` | Databricks workflow execution contract | Any schedule, cluster, or parameter change |
| `docs/project/phase1_leadership_summary.md` | Leadership-facing status and go/no-go snapshot | After each Phase checkpoint |

## Architectural Decisions and Why They Matter

### 1. Importable Python functions over notebook cells

The training pipeline is structured as plain Python functions in `src/training/train_xgboost.py` (`_validate_input_dataframe`, `split_train_val_test`, `_infer_feature_columns`, `run_training`) rather than notebook cells.

**Why this is architecturally significant:**

| Concern | Notebook cell approach | This repo's approach |
|---|---|---|
| Testability | Cells cannot be imported or called by pytest | Functions imported directly in `tests/test_training.py` |
| Code path consistency | Notebook runs are environment-dependent | Same function runs locally in pytest AND in Databricks job |
| Regression safety | No safety net — cell change is silently live | A broken function fails pytest before reaching Databricks |
| Traceability | Notebook history is fragile and non-linear | Git diff shows exactly what changed in which function |
| CMMI evidence | Manual review of output cells | Automated gate flags logged to MLflow on every run |

**The key guarantee:** the function tested in `tests/test_training.py` is the exact same function that runs inside `jobs/train_job.yaml` on Databricks. There is no gap between what was tested and what was deployed.

### 2. One entrypoint, two contexts

`src/training/train_xgboost.py` is both a locally runnable Python script and the Databricks job task target. Parameters are passed via `argparse`, which works identically from the command line and from the Databricks job parameter block in `jobs/train_job.yaml`. This means:
- Local dev validation: `python src/training/train_xgboost.py --input-csv data/...`
- Production run: Databricks executes the same file with the same arguments from the cluster.

Production trigger policy:
- Databricks-scheduled Jobs are the default Phase 0 production trigger path.
- UI-triggered runs are allowed for diagnostics but are not the standard production mechanism.
- Local script runs are preflight validation and do not replace Databricks production evidence.

No notebook conversion, no environment translation, no hidden state.

### 3. Governance logic is code, not a checklist

CMMI gate logic lives in `src/governance/cmmi_l5_metrics.py` as callable Python and is validated by `tests/test_cmmi_l5_metrics.py`. This means:
- Gate thresholds are version-controlled and auditable.
- A regression in gate logic (e.g. threshold accidentally widened) is caught by a test.
- Evidence is emitted programmatically to MLflow on every run — not filled in manually after the fact.

A notebook-only or spreadsheet-based governance approach cannot provide these guarantees.

---

## Minimum Team Operating Rule (CMMI L5)
1. Do not move notebook logic into production paths without a requirement and tests.
2. Do not close a phase without metric evidence, gate status, and documented decision.
3. Do not treat a metric snapshot as complete unless baseline comparison is captured.

## Review Cadence
- Weekly during active migration.
- At each phase closeout.
- Immediately after any workflow, metric, or governance model change.
