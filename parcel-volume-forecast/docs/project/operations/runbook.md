
# Project - Operational Runbook
# Model: Multi Client Forecast IB Uplift
# Owner: Central Analytics

---

Purpose: this document explains the repo-level workflow clearly: how to validate the code with tests, how to run the training model locally, and how to trigger the current available Databricks runs.

Production operating rule:
- Production training is repo-backed and must execute the repository entrypoint `src/training/train_xgboost.py`.
- Notebook-backed runs are for exploration or diagnostics only and are not the approved long-term production path.
- Databricks-scheduled Jobs are the preferred Phase 0 trigger mechanism when shared job compute is available.
- CLI-triggered runs that log to MLflow are allowed for debugging, but they are non-production evidence and must not be used for promotion decisions.

Runtime source parameter rule (Phase 0):
- Replace hardcoded table references with central config defaults.
- Keep loader interfaces explicit; resolve runtime source values in orchestration.
- Use precedence `CLI -> env -> config default` for local/preflight resolution.
- Production Jobs/CI should pass runtime source parameters explicitly.

Current live-table production target (as of 2026-07-06):
- Active Databricks job id: `745290703540915`
- Active Unity Catalog source table: `evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35`

## Recommended operating flow

### When to use the staged refinery path

Use the new Stage 2/Stage 3 refinery path whenever the training input comes from a live Unity Catalog table or another large, operational source. This is the default expectation for production training because it keeps the row-level contract explicit and prevents invalid rows from reaching the model.

Use the simpler CSV path when:
- you are doing a quick local smoke test,
- you need deterministic fixture data for debugging, or
- the input file is small and already curated.

Use the live-table refinery path when:
- the source is a Databricks table with production freshness requirements,
- the dataset may contain sparse or noisy rows,
- you need guardrail evidence for governance review, or
- you want the pipeline to fail fast before training on a bad slice.

### What the refinery stages do

- Stage 2 enforces the required column contract, temporal cutoff, non-null checks, non-null target insulation, and positive baseline filter before data reaches pandas/XGBoost.
- Stage 3 evaluates the resulting row volume against the approved guardrail envelope and returns one of three outcomes: nominal success, approved deviation, or hard failure.

### Guardrail outcomes and operator action

- Nominal operation: drop fraction is at or below 2% and the run continues normally.
- Approved deviation: the slice is still above the minimum acceptable volume but inside the approved tolerance envelope; log the governance warning and continue only if the business owner accepts the risk.
- Hard breach: the slice falls below the minimum row fraction or exceeds the maximum allowed drop fraction; stop the run and escalate the data issue.

### Practical guidance for local and Databricks runs

- For local smoke tests, prefer the CSV path unless you are explicitly validating the live-table contract.
- For Databricks production runs, use the live-table path only after confirming the source table has the expected columns and values.
- Before triggering a live-table run after a data-source change, execute a SQL parity count with the same Stage 2 predicates (`DATE_SUB(current_date(), 730)`, non-null date/actual, `parcel_volume > 0`, `preadvice_date <= current_date()`, `median_4wk_volume > 10`) to verify row volume is above the Stage 3 minimum threshold.
- If the run logs a governance warning, review the volume drop in the training run report and decide whether the live-table source still meets the operational contract.
- If the run fails with a Stage 3 error, treat it as a data-quality incident and investigate the upstream source before retrying.


Use the steps below in order:

1. Run the tests first (validation gate)
   - Command: `python -m pytest`
   - Use this after code changes, before a training run, and before promotion.
   - This checks the transform contract, training validation logic, and CMMI governance rules.

### Report artifact commands (new)

- Unit-test report artifacts (summary + per-test status):

```bash
python scripts/run_tests_with_report.py
```

- Targeted unit-test report (example):

```bash
python scripts/run_tests_with_report.py tests/test_training.py -q
```

- Custom output directory:

```bash
python scripts/run_tests_with_report.py --output-dir reports/tests/latest
```

Generated files:
- `reports/tests/latest/junit.xml`
- `reports/tests/latest/test_run_summary.json`
- `reports/tests/latest/test_run_summary.html`

Training run report artifacts are generated automatically by `src/training/train_xgboost.py` and logged to MLflow under `reports/` as:
- `run_summary.json`
- `run_summary.html`

The run summary now includes operational and governance sections used for promotion review:
- `operational_archetype_briefing` (cohort rows, business SMAPE, threshold, workflow impact)
- `promotion_context` (metric, threshold, observed value, explicit block reason)
- `config_snapshot` (runtime thresholds and cohort cut points)

Current promotion gate policy:
- Primary quality gate: `test_smape_volume <= 40.0`.
- Calibrated 2026-07-06: live-table naive baseline is ~33.7%; 15% (CSV-era) was unreachable at daily/client granularity.
- Archetype hard gates: Anchors `<= 7.5`, Dials `<= 13.0`, Phantoms `<= 32.0`.
- Spikers `<= 24.0` is warning-only (does not block promotion by itself).
- Final recommendation requires quality gate pass and all CMMI gates pass.

2. Run the model locally for a smoke test (optional but recommended)
   - Command: `python src/training/train_xgboost.py --input-csv data/multi_client_ib_uplift.csv --experiment "parcel-volume-forecast-local-smoke" --dataset-version v1 --run-mode debug`
   - Use this only as a preflight check before triggering Databricks, not as proof that the Databricks production run succeeded.

### Local smoke run playbook

Command (PowerShell):
- `$env:PYTHONPATH='.'; python -m src.training.train_xgboost --input-csv data/multi_client_ib_uplift.csv --experiment "parcel-volume-forecast-local-smoke" --dataset-version v1 --run-mode debug`

What it does:
- Runs one local smoke training run using repository code.

Parameters and where to set them:
- `--input-csv`: input file path; set directly in the command.
- `--experiment`: MLflow experiment name; set directly in the command.
- `--dataset-version`: dataset tag logged to MLflow; set directly in the command.
- `--run-mode`: execution mode (`debug`/`production`); set directly in the command.
- `PYTHONPATH`: local import path; set in the shell before the command.

What should happen on success:
- Training completes with process exit code 0.
- A new MLflow run is created.
- Core metrics are logged (for example `test_smape_target`, `val_smape_target`).
- CMMI process metrics and gate flags are logged.
- Report artifacts are generated under MLflow artifacts path `reports/`:
   - `run_summary.json`
   - `run_summary.html`

How to change behavior:
- Change `--input-csv`, `--experiment`, `--dataset-version`, or `--run-mode` in the command.
- For model defaults, update `src/config.py`.

### Input parameters: local vs Databricks

| Parameter | Local smoke run | Databricks serverless job |
|---|---|---|
| `--input-csv` | `data/multi_client_ib_uplift.csv` | `evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35` |
| `--experiment` | any name (file-backed MLflow) | `/Shared/forecasting/parcel-volume-forecast` |
| `--dataset-version` | `v1` | `v1` |
| `--run-mode` | `debug` recommended | `production` for governed runs; `debug` for ad-hoc |
| `PYTHONPATH` | must set `PYTHONPATH=.` | not needed — entrypoint bootstraps the repo root |

### Maintained Databricks job configuration

The maintained production job configuration is:

**Live table job** (`jobs/job-live-table-reset.json`)
- Reads training data directly from Unity Catalog table
- Input: `evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35` (table name)
- Use when: you have a live data pipeline and want automatic data freshness
- Setup: ensure table exists in your Databricks catalog and has required columns
- Advantage: no manual data uploads needed; data is fresh from upstream pipeline

To apply the maintained job configuration:
1. Apply the live-table configuration: `databricks jobs reset --job-id 745290703540915 --json @jobs/job-live-table-reset.json`
2. Verify configuration in Databricks Workflows UI
3. Test with a manual run before relying on scheduled runs

Ensure your source system populates the table with required columns matching the training contract.

3. Trigger a Databricks run
   - Use one of the currently available methods below.
   - All of these ultimately run the same repository-backed training entrypoint and log to MLflow.

### Tests vs model run
- Tests are separate from the training job. They validate the code and logic, but they do not start the model training by themselves.
- The model run executes the production entrypoint in `src/training/train_xgboost.py` and performs the actual training, evaluation, and MLflow logging.
- For governance and auditability, run tests in local validation or CI first, then trigger the training job.

## Current trigger options

Use the option that matches the situation you are in right now.

1. Databricks Jobs UI `Run now`
   - Command: click `Run now` in Databricks Workflows UI.
   - What it does: triggers the configured job immediately.
   - Parameters and location: use job default parameters from Databricks job settings.

2. Databricks schedule inside Workflows
   - Command: configure and enable schedule in Databricks Workflows UI.
   - What it does: runs the job automatically on the configured schedule.
   - Parameters and location: use job default parameters from Databricks job settings.

3. Databricks CLI `jobs run-now`
   - Command: use CLI directly with `job_id` or inline JSON overrides.
   - What it does: triggers one ad-hoc run from local terminal or CI.
   - Parameters and location:
   - `job_id`: passed directly in the command.
   - `python_params`: optional inline JSON override list.

```powershell
# Production run (live table defaults)
databricks jobs run-now 745290703540915

# Debug run (live table override)
databricks jobs run-now --json '{"job_id":745290703540915,"python_params":["--input-csv","evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35","--dataset-version","v1_live","--run-mode","debug"]}'
```

4. Databricks REST API `jobs/run-now`
   - Command: POST `/api/2.1/jobs/run-now`.
   - What it does: triggers one run via API and returns `run_id`.
   - Parameters and location: set `job_id` and optional `python_params` in request JSON body.

```bash
curl -n -X POST https://<databricks-instance>/api/2.1/jobs/run-now \
  -H 'Content-Type: application/json' \
   -d '{"job_id": 745290703540915, "python_params": ["--input-csv", "evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35", "--dataset-version", "v1_live", "--run-mode", "debug"]}'
```

5. Databricks SDK
   - Command: call `client.jobs.run_now(...)`.
   - What it does: triggers one run from application code.
   - Parameters and location: set `job_id` and optional `python_params` in SDK call arguments.

```python
from databricks.sdk import WorkspaceClient

client = WorkspaceClient()
resp = client.jobs.run_now(
   job_id=745290703540915,
    python_params=[
      "--input-csv", "evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35",
      "--dataset-version", "v1_live",
        "--run-mode", "debug",
    ],
)
run_id = resp.run_id
```

### Notes

- CLI/REST/SDK triggers start jobs immediately; UI interaction is not required.
- For run status, use `run_id` from CLI/REST/SDK and query Databricks run state.

For operational validation, promotion, rollback, and contacts, see the other docs in `docs/project/`.

### Full workflow trigger
- The workflow definition is captured in `jobs/train_job.yaml`.
- The job executes the production entrypoint `src/training/train_xgboost.py`.
- This run performs the full training pipeline: ingest, preprocessing, feature transforms, split, training, evaluation, MLflow logging, and CMMI metric capture.

### Verification rule
- Verify Databricks production success from the Databricks run state, logs, MLflow metrics, model artifacts, and governance report artifacts.
- Do not use a post-run local smoke execution as a substitute for Databricks production verification.

### Local debug artifacts policy
- Keep ad-hoc debugging scripts and outputs under `local-debug/` only.
- Do not commit local debug artifacts to Git; `local-debug/.gitignore` is the enforcement point.

