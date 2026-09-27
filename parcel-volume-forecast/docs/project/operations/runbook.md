
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

## Recommended operating flow

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
| `--input-csv` | `data/multi_client_ib_uplift.csv` | `/Workspace/Shared/forecasting/multi_client_ib_uplift.csv` |
| `--experiment` | any name (file-backed MLflow) | `/Shared/forecasting/parcel-volume-forecast` |
| `--dataset-version` | `v1` | `v1` |
| `--run-mode` | `debug` recommended | `production` for governed runs; `debug` for ad-hoc |
| `PYTHONPATH` | must set `PYTHONPATH=.` | not needed — entrypoint bootstraps the repo root |

### Two job configurations available

The training script supports both CSV file and Unity Catalog table inputs. Two job configurations are provided:

**CSV-based job** (`jobs/job-587032785657077-reset.json`)
- Reads training data from uploaded CSV file in Databricks workspace
- Input: `/Workspace/Shared/forecasting/multi_client_ib_uplift.csv`
- Use when: you have static training data or want to control exactly which data is used
- Setup: upload CSV file once with `databricks workspace import` (see command below)

**Live table job** (`jobs/job-587032785657077-live-data.json`)
- Reads training data directly from Unity Catalog table
- Input: `forecasting_prod.landing.multi_client_ib_uplift` (table name)
- Use when: you have a live data pipeline and want automatic data freshness
- Setup: ensure table exists in your Databricks catalog and has required columns
- Advantage: no manual data uploads needed; data is fresh from upstream pipeline

To switch jobs:
1. Apply the desired job configuration: `databricks jobs reset --job-id 587032785657077 --json @jobs/job-587032785657077-reset.json` (CSV) or `databricks jobs reset --job-id 587032785657077 --json @jobs/job-587032785657077-live-data.json` (live table)
2. Verify configuration in Databricks Workflows UI
3. Test with a manual run before relying on scheduled runs

Data upload for Databricks CSV option (run once before first trigger, or when training data changes):

```powershell
databricks workspace import /Shared/forecasting/multi_client_ib_uplift.csv --file data/multi_client_ib_uplift.csv --format RAW --overwrite
```

For the live table option, ensure your source system populates the table with required columns matching the CSV schema.

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
   - Command: use CLI with JSON payload file.
   - What it does: triggers one ad-hoc run from local terminal or CI.
   - Parameters and location:
     - `job_id`: set in `run-trigger.json`.
     - `python_params`: optional override list in `run-trigger.json`.
     - `run-trigger.json` location: repository root (or current working directory).

```powershell
# Production run — uses job-configured parameters, no override needed
'{ "job_id": 587032785657077 }' | Out-File -Encoding ascii run-trigger.json
databricks jobs run-now --json "@run-trigger.json"

# Debug run — override input path and run mode
'{"job_id":587032785657077,"python_params":["--input-csv","/Workspace/Shared/forecasting/multi_client_ib_uplift.csv","--dataset-version","v1","--run-mode","debug"]}' | Out-File -Encoding ascii run-trigger.json
databricks jobs run-now --json "@run-trigger.json"

# Optional cleanup of temporary payload file
Remove-Item run-trigger.json -ErrorAction SilentlyContinue
```

4. Databricks REST API `jobs/run-now`
   - Command: POST `/api/2.1/jobs/run-now`.
   - What it does: triggers one run via API and returns `run_id`.
   - Parameters and location: set `job_id` and optional `python_params` in request JSON body.

```bash
curl -n -X POST https://<databricks-instance>/api/2.1/jobs/run-now \
  -H 'Content-Type: application/json' \
  -d '{"job_id": 587032785657077, "python_params": ["--input-csv", "/Workspace/Shared/forecasting/multi_client_ib_uplift.csv", "--dataset-version", "v1", "--run-mode", "debug"]}'
```

5. Databricks SDK
   - Command: call `client.jobs.run_now(...)`.
   - What it does: triggers one run from application code.
   - Parameters and location: set `job_id` and optional `python_params` in SDK call arguments.

```python
from databricks.sdk import WorkspaceClient

client = WorkspaceClient()
resp = client.jobs.run_now(
    job_id=587032785657077,
    python_params=[
        "--input-csv", "/Workspace/Shared/forecasting/multi_client_ib_uplift.csv",
        "--dataset-version", "v1",
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

