
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
   - Command: `python src/training/train_xgboost.py --input-csv data/multi_client_ib_uplift.csv --experiment "/Shared/forecasting/parcel-volume-forecast" --dataset-version v1`
   - Use this only as a preflight check before triggering Databricks, not as proof that the Databricks production run succeeded.

### Local smoke run playbook

Purpose:
- Validate the full repository training path on a small local dataset before Databricks execution.

What data it uses by default:
- Input CSV: `data/multi_client_ib_uplift.csv`
- Date column: `event_date`
- Target source columns: `actual_volume` and `rolling_4w_median`

Prerequisites:
- Install dependencies from `requirements-dev.txt`.
- Run from repository root.
- Ensure package imports resolve locally.

Recommended commands (PowerShell):
- Basic smoke run:
   - `$env:PYTHONPATH='.'; python src/training/train_xgboost.py --input-csv data/multi_client_ib_uplift.csv --experiment "/Shared/forecasting/parcel-volume-forecast" --dataset-version v1`
- Module-mode run (alternative):
   - `$env:PYTHONPATH='.'; python -m src.training.train_xgboost --input-csv data/multi_client_ib_uplift.csv --experiment "/Shared/forecasting/parcel-volume-forecast" --dataset-version v1`

What should happen on success:
- Training completes with process exit code 0.
- A new MLflow run is created.
- Core metrics are logged (for example `test_smape_target`, `val_smape_target`).
- CMMI process metrics and gate flags are logged.
- Report artifacts are generated under MLflow artifacts path `reports/`:
   - `run_summary.json`
   - `run_summary.html`

How to modify smoke-run behavior:
- Use a different input file:
   - change `--input-csv` to another CSV path.
- Use a different experiment namespace:
   - change `--experiment` value.
- Tag a different dataset version:
   - change `--dataset-version` value.
- Change model/split/governance defaults:
   - update grouped values in `src/config.py`.
- Change training orchestration flow:
   - update `src/training/train_xgboost.py`.

Troubleshooting quick checks:
- Import error `No module named src`:
   - set `PYTHONPATH=.` before running.
- Data validation failure:
   - check required columns and non-null/non-negative constraints in `src/training/data_validation.py`.
- Missing report artifacts:
   - check report helpers in `src/reporting/training_report.py` and MLflow artifact directory.

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
   - Best for quick manual checks or controlled diagnostics.
   - Still uses the job's configured compute, so it will fail if the job identity cannot create or attach to cluster compute.

2. Databricks schedule inside Workflows
   - Best for the Phase 0 operating path when shared job compute is available.
   - This is the standard recurring trigger path in Databricks.

3. Databricks CLI `jobs run-now`
   - Best for hands-on debugging and controlled ad-hoc runs.
   - Mark these as debug evidence when using `--run-mode debug`.

```powershell
$jobId = python -c "from src.config import DATABRICKS_JOB_ID; print(DATABRICKS_JOB_ID)"
databricks jobs run-now --job-id $jobId --python-params '["--input-csv","/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv","--dataset-version","v1","--run-mode","debug"]'
```

4. Databricks REST API `jobs/run-now`
   - Best for scripts and external automation.
   - Use this when you want a direct API trigger and a `run_id` response.

```bash
curl -n -X POST https://<databricks-instance>/api/2.1/jobs/run-now \
  -H 'Content-Type: application/json' \
   -d '{"job_id": 610583632972805, "python_params": ["--input-csv", "/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv", "--dataset-version", "v1", "--run-mode", "debug"]}'
```

5. Databricks SDK
   - Best when you want programmatic control from Python or Java.

```python
from databricks.sdk import Workspace

client = Workspace()
resp = client.jobs.run_now(job_id=<JOB_ID>, python_params=["--input-csv", "/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv", "--dataset-version", "v1", "--run-mode", "debug"])
run_id = resp.run_id
```

6. Notebook-launcher POC
   - Best for proving repo code execution when job-compute permissions are blocked.
   - Notebook is only a launcher; repository code does the actual work.
   - Always run in debug mode and treat as non-production evidence.

```python
from src.training import run_notebook_launcher_poc

run_notebook_launcher_poc(
    input_csv="/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv",
    experiment_name="/Shared/forecasting/parcel-volume-forecast",
    dataset_version="v1-poc",
)
```

### Notes

- CLI/REST/SDK triggers are independent and start jobs immediately; you do not need to press "Run" in the UI first.
- Use `--run-mode debug` for ad-hoc validation runs.
- REST responses include `run_id`; poll `GET /api/2.1/jobs/runs/get?run_id=<run_id>` to monitor state.
- Authentication: for local use configure `databricks configure --token` or use `~/.databrickscfg`.

For operational validation, promotion, rollback, and contacts, see the other docs in `docs/project/`.

### Full workflow trigger
- The workflow definition is captured in `jobs/train_job.yaml`.
- The job executes the production entrypoint `src/training/train_xgboost.py`.
- This run performs the full training pipeline: ingest, preprocessing, feature transforms, split, training, evaluation, MLflow logging, and CMMI metric capture.

### Verification rule
- Verify Databricks production success from the Databricks run state, logs, MLflow metrics, model artifacts, and governance report artifacts.
- Do not use a post-run local smoke execution as a substitute for Databricks production verification.

### Copilot / Genie role vs job trigger

- `Copilot` (and Genie) are **authoring assistants**: they help draft SQL, notebooks, and code that developers then review and commit. They are not the runtime mechanism for production triggers.
- The Databricks job trigger is performed by the Databricks UI, CLI, or REST API (examples above). Copilot can generate the CLI or REST snippet as shown, but execution must be done by an authenticated user or CI/CD system (e.g., Jenkins).
- For audits and CMMI evidence, always prefer automated runs via the Databricks CLI or REST API from CI (Jenkins/GitHub Actions) so the run is reproducible and traceable.

# Project - Operational Runbook
# Model: Multi Client Forecast IB Uplift
# Owner: Central Analytics

---

Purpose: This runbook documents only the repository-level workflow trigger for running the production training job. Operational validation, local dev instructions, promotion, rollback, and contact lists live in separate docs.

## Repo-level Workflow Trigger

1. Upload the latest training extract to `/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv`.
2. Trigger the Databricks Workflow `parcel-volume-forecast-train`.

### How to trigger the Databricks job (repo-level options)

- Databricks UI: open the job named `parcel-volume-forecast-train` and click "Run now" only for diagnostics or controlled manual execution.
- Databricks CLI (automation):

```bash
# Authenticate with Databricks CLI first (configure host + token)
databricks jobs run-now --job-id <JOB_ID> --python-params '["--input-csv","/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv","--experiment","/Shared/forecasting/parcel-volume-forecast","--dataset-version","v1"]'
```

- Databricks REST API (CI/CD pipelines):

```bash
curl -n -X POST https://<databricks-instance>/api/2.1/jobs/run-now \
  -H 'Content-Type: application/json' \
   -d '{"job_id": <JOB_ID>, "python_params": ["--input-csv", "/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv", "--experiment", "/Shared/forecasting/parcel-volume-forecast", "--dataset-version", "v1"]}'
```

Replace `<JOB_ID>` and `<databricks-instance>` with your Databricks job id and host. Parameters passed in `python_params` are available to the Spark Python task and should be consumed by the Python entrypoint configured in `jobs/train_job.yaml`.

### Copilot / Genie role vs job trigger

- `Copilot` and similar authoring assistants help draft code, notebooks, and CLI/REST snippets, but they do not execute jobs in your environment.
- Use the Databricks UI, CLI, or REST API for actual job execution. For reproducibility and auditability, prefer CI/CD-triggered CLI or REST execution over manual UI execution.

For other operational procedures (validation, local debug, promotion, rollback, contacts) see their respective docs in `docs/project/`.

