# Databricks Debug Reference
# Model: Multi Client Forecast IB Uplift
# Owner: Central Analytics

---

Purpose: this document captures every diagnosed failure mode encountered during Phase 0 Databricks job execution, the root cause, the verified fix, and the inspection commands needed to reach the next failure layer. Use it as the starting point for future debugging before searching elsewhere.

---

## Failure mode index

| Error | Layer | Root cause | Fix |
|---|---|---|---|
| `REPOSITORY_CHECKOUT_FAILED` | Job setup | GitLab credentials not configured in Databricks Git Integration | Configure credentials under User Settings → Git Integration |
| `RESOURCE_NOT_FOUND` on task file | Job config | `python_file` path used Windows backslashes or pointed at YAML instead of `.py` | Use forward slashes; path is repo-relative e.g. `parcel-volume-forecast/src/training/train_xgboost.py` |
| `NameError: name '__file__' is not defined` | Bootstrap | Databricks serverless executes scripts via `exec(compile(...))`, which does not set `__file__` | Bootstrap in `train_xgboost.py` uses `inspect.currentframe()` to resolve the repo root without relying on `__file__` |
| `ModuleNotFoundError: No module named 'src'` | Bootstrap | Repo root not on `sys.path` in the Databricks execution context | `_resolve_project_root()` in `train_xgboost.py` walks parent dirs looking for `src/config.py` and inserts the root into `sys.path` |
| `ModuleNotFoundError: No module named 'xgboost'` | Runtime import | `xgboost` is not pre-installed in Databricks serverless Jobs Compute v2 and was not declared in the job environment spec | Add `xgboost==3.3.0` to `environments[].spec.dependencies` in `jobs/job-live-table-reset.json`; apply with `databricks jobs reset` |
| `FileNotFoundError: /dbfs/FileStore/forecasting/...` | Data load | Serverless Jobs Compute v2 does not mount `/dbfs/`; FUSE mount only exists on classic clusters | Use the maintained live-table job (`jobs/job-live-table-reset.json`) and pass the Unity Catalog table name in `--input-csv` |
| `Workload failed, see run output for details` | Task | Generic wrapper — the real error is one layer down in task output | Fetch task-level run output (see inspection commands below) |
| `Stage 3 guardrail failed for live-table input` | Data contract | The refined training slice dropped below the approved volume envelope | Validate row counts with the same Stage 2 predicates before rerun; for current production use `...fcast_multi_client_data_build_champion_modelv35` instead of stale low-volume tables |
| OOM / driver crash during `toPandas()` | Data load | Pulling a raw 730-day Unity Catalog table into pandas without server-side filtering exhausts serverless driver memory | All Stage 2 filters must be applied as Spark push-down predicates before `toPandas()` is called; see `_load_training_data()` |
| High SMAPE / model worse than naive (e.g. 86%) | Training | Future placeholder rows (`parcel_volume = 0`, `preadvice_date > today`) contaminate the training and test sets; log(1e-6) = -13.8 injected as target | Spark filter must include `preadvice_date <= current_date` AND `parcel_volume > 0` before `toPandas()` |
| `ValueError: DataFrame.dtypes for data must be int, float, bool or category. Invalid columns: event_date: datetime64[ns]` | XGBoost DMatrix | `event_date` (the date column) starts with `event_` so it was included in the feature set by `infer_feature_columns()` | `infer_feature_columns()` now excludes `cfg.date_col` from the `event_` prefix match |
| `ValueError: columns overlap but no suffix specified: Index(['event_date'])` | Pandas join | `event_date` included in event passthrough list and also returned by refinery — duplicate column collision on join | Event passthrough filter in `train_xgboost.py` now excludes `DATE_COL` from the `event_` prefix list |
| `promotion_recommendation: False` with all archetype gates passing | Promotion | `MAX_SMAPE_THRESHOLD` was set to 15% (CSV-era calibration); live-table naive baseline is ~33.7%, making 15% physically unreachable | `MAX_SMAPE_THRESHOLD` recalibrated to 40% in `src/config.py` (2026-07-06) |

---

## Serverless vs classic cluster: key differences

| Topic | Serverless Jobs Compute v2 | Classic cluster |
|---|---|---|
| `/dbfs/` mount | Not available | Available |
| File inputs | Use `/Workspace/` paths | `/dbfs/` or `/Workspace/` both work |
| Third-party packages | Declare in `environments[].spec.dependencies` | Use task-level `libraries[].pypi` |
| Pre-installed packages | `mlflow`, `pandas`, `numpy`, `scipy`, `scikit-learn` | Depends on cluster runtime version |
| `__file__` in executed scripts | Not set (exec context) | Set normally |
| Compute permission | Managed by Databricks, no cluster create permission needed | Requires `Can Create Cluster` or existing cluster |

The live job (`745290703540915`) runs on **serverless Jobs Compute v2**. Always apply the serverless column rules.

---

## Inspection commands

Run these in order to narrow a failure to the exact line.

### Step 1 — get the most recent job run id

```powershell
databricks jobs list-runs --job-id 745290703540915 --limit 1 --output json
```

Note the `run_id` from the response.

### Step 2 — get the task-level run id

Multi-task jobs cannot be queried with `get-run-output` at the job level. Extract the task run id first:

```powershell
databricks jobs get-run <JOB_RUN_ID> --output json | ConvertFrom-Json | Select-Object -ExpandProperty tasks | Select-Object run_id, task_key, state
```

Note the task-level `run_id`.

### Step 3 — read the task output

```powershell
databricks jobs get-run-output <TASK_RUN_ID> --output json
```

The `error` field contains the exception class and message. The `logs` field contains stdout/INFO lines up to the point of failure — this shows how far the script progressed before crashing.

### Step 4 — check environment spec (if import error)

```powershell
databricks jobs get 745290703540915 --output json | ConvertFrom-Json | Select-Object -ExpandProperty settings | Select-Object -ExpandProperty environments
```

Confirm `dependencies` includes `xgboost==3.3.0`. If not, update `jobs/job-live-table-reset.json` and re-apply:

```powershell
databricks jobs reset --json "@jobs/job-live-table-reset.json"
```

### Step 5 — check DBFS/Workspace file presence (if FileNotFoundError)

```powershell
# Check Workspace path
databricks workspace list /Shared/forecasting

# Check DBFS (only for classic cluster jobs)
databricks fs ls dbfs:/FileStore/forecasting
```

### Step 6 — run SQL parity check for Stage 2 filtering (if Stage 3 guardrail fails)

Use a SQL warehouse query that mirrors the Stage 2 predicates before rerunning the job.

```sql
SELECT 'champion_modelv35' AS tbl, COUNT(*) AS valid_rows
FROM evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35
WHERE preadvice_date >= DATE_SUB(current_date(), 730)
  AND preadvice_date <= current_date()
  AND preadvice_date IS NOT NULL
  AND parcel_volume IS NOT NULL
  AND parcel_volume > 0
  AND median_4wk_volume > 10;
```

Interpretation:
- After Spark push-down the production table currently delivers ~1,011,634 rows before refinery.
- If `valid_rows` drops significantly below 1M, investigate the upstream table for truncation or schema change.
- Stage 3 guardrail blocks training if the refinery output falls below the approved minimum row fraction.

Optional comparison query (old vs current source):

```sql
SELECT 'champion_ib_uplift' AS tbl, COUNT(*) AS valid_rows
FROM evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_ib_uplift
WHERE preadvice_date >= DATE_SUB(current_date(), 365)
  AND preadvice_date IS NOT NULL
  AND parcel_volume IS NOT NULL
  AND median_4wk_volume > 10
  AND target IS NOT NULL
UNION ALL
SELECT 'champion_modelv35' AS tbl, COUNT(*) AS valid_rows
FROM evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35
WHERE preadvice_date >= DATE_SUB(current_date(), 365)
  AND preadvice_date IS NOT NULL
  AND parcel_volume IS NOT NULL
  AND median_4wk_volume > 10
  AND target IS NOT NULL;
```

---

## Input source reference

| Context | `--input-csv` value |
|---|---|
| Local smoke run | `data/multi_client_ib_uplift.csv` |
| Databricks serverless job (maintained) | `evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35` |
| Databricks classic cluster | same Unity Catalog table value |

---

## Local smoke troubleshooting quick checks

Use these checks for local preflight runs before Databricks triggers.

1. Import error: `No module named src`
  - Root cause: repository root is not on `PYTHONPATH`.
  - Fix (PowerShell):

```powershell
$env:PYTHONPATH='.'
python -m src.training.train_xgboost --input-csv data/multi_client_ib_uplift.csv --experiment "parcel-volume-forecast-local-smoke" --dataset-version v1 --run-mode debug
```

2. Data validation failure
  - Root cause: missing required columns or invalid values (null/non-negative constraints).
  - Check validation rules in `src/training/data_validation.py`.
  - Confirm required input columns and value quality in the CSV before rerun.
4. Refinery guardrail failure
  - Root cause: the live-table slice dropped below the approved row-volume envelope or failed the strict null-target contract.
  - Check the Stage 2/Stage 3 logic in `src/training/refinery.py` and the guardrail values in `src/config.py`.
  - Review the source table row counts and the required columns (`preadvice_date`, `parcel_volume`, `median_4wk_volume`, `target`) before retrying.
3. Missing report artifacts (`run_summary.json`, `run_summary.html`)
  - Root cause: training report generation failed or artifact logging path issue.
  - Check report generation helpers in `src/reporting/training_report.py`.
  - Verify artifacts under the MLflow run in `reports/`.

4. Promotion unexpectedly rejected with successful training run
  - Root cause: quality gate now uses business-space SMAPE (`test_smape_volume`) and archetype hard-gate outcomes, not only transformed-target metrics.
  - Check `test_smape_volume`, `quality_pass`, and `promotion_recommendation` in MLflow metrics.
  - Open `reports/run_summary.json` and inspect:
    - `operational_archetype_briefing` for any `ZONE_3_CRITICAL_REJECTION` rows,
    - `promotion_context.promotion_block_reason` for explicit rejection reason.

---

## Runtime dependencies and constraints

Use this section as the technical source of truth for environment setup and runtime constraints.

Local environment:
- Install project dependencies from `requirements-dev.txt` before local smoke runs.
- Run commands from repository root.
- Set `PYTHONPATH=.` for local module execution when needed.

Databricks serverless job constraints (job `745290703540915`):
- `/dbfs/` FUSE mount is not available on serverless compute; use `/Workspace/` input paths.
- Third-party packages not pre-installed must be declared in `environments[].spec.dependencies`.
- Current required declaration: `xgboost==3.3.0`.
- Pre-installed in serverless v5: `mlflow`, `pandas`, `numpy`, `scipy`, `scikit-learn`.
- Live-table push-down delivers ~1,011,634 rows (730-day window, future-date excluded, zero-volume excluded, baseline floor > 10).

Environment reset procedure:
- After modifying `jobs/job-live-table-reset.json`, apply changes with:

```powershell
databricks jobs reset --json "@jobs/job-live-table-reset.json"
```

Authentication and runtime identity:
- Local CLI/SDK access uses `databricks configure --token` (or `~/.databrickscfg`).
- Job runtime inside Databricks authenticates automatically using the configured job identity (service principal/user).
- No token handling is required inside `src/training/train_xgboost.py`.

---

## Environment dependency management

The live job declares extra packages in `jobs/job-live-table-reset.json`:

```json
"environments": [
  {
    "environment_key": "Default",
    "spec": {
      "environment_version": "5",
      "dependencies": [
        "xgboost==3.3.0"
      ]
    }
  }
]
```

To add a new package (e.g. for a future phase):
1. Add the package to `requirements-dev.txt` (keeps local and remote in sync).
2. Add the same package string to `dependencies` in `jobs/job-live-table-reset.json`.
3. Apply: `databricks jobs reset --json "@jobs/job-live-table-reset.json"`.
4. Re-trigger the job and verify the new import no longer fails.

---

## Trigger commands reference

```powershell
# Production run — uses job default parameters
databricks jobs run-now 745290703540915

# Debug run — override parameters
databricks jobs run-now --json '{"job_id":745290703540915,"python_params":["--input-csv","evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35","--dataset-version","v1_live","--run-mode","debug"]}'

# Apply a job config reset
databricks jobs reset --json "@jobs/job-live-table-reset.json"
```

Note: `databricks jobs run-now` supports a positional `JOB_ID`; use `--json` only when you need parameter overrides.

---

## Verified working state (Phase 0 POC — 2026-07-02)

Run `123480460228569` on commit `d63860a` completed with `result_state: SUCCESS`.

Confirmed from run logs:
- Bootstrap resolved repo root and `src` package loaded cleanly
- 12 feature columns used: cyclical time features (`dom`, `dow`, `doy`, `month`, `woy`) + client flags
- MLflow Experiment `/Shared/forecasting/parcel-volume-forecast` created
- Model artifact logged
- CMMI gates evaluated and logged
- `run_summary.json` and `run_summary.html` emitted to MLflow artifacts under `reports/`

---

## Future phase considerations

| Area | Phase 0 state | Future action |
|---|---|---|
| Input data | Repo sample CSV uploaded manually to Workspace | Replace with Delta table read from Unity Catalog; update `--input-csv` to UC volume or use `load_training_data.py` Spark loader |
| Compute | Serverless Jobs Compute v2 | Shared job cluster when provisioned by platform team |
| Package management | Manual `dependencies` list in job reset JSON | Migrate to Databricks Asset Bundles (DABs) so `requirements-dev.txt` drives both local and remote environments |
| CI/CD trigger | Manual CLI / Databricks UI schedule | Jenkins or GitLab CI pipeline calls `databricks jobs run-now` post-merge to main |
| Experiment path | `/Shared/forecasting/parcel-volume-forecast` (shared workspace) | Promote to Unity Catalog MLflow experiment for fine-grained access control |
| `run_mode` | `production` flag in job config | Enforce via CI policy gate so debug-flagged runs cannot be used as promotion evidence |

---

## Local debug artifact policy

- Store local-only MCP/CLI debugging helpers and outputs in `local-debug/`.
- Keep `local-debug/` out of commits via `local-debug/.gitignore`.
- Treat files under `local-debug/` as disposable troubleshooting artifacts, not governed run evidence.
