# Parcel Volume Forecast — Technical Onboarding

This document is the definitive structural architecture and onboarding reference for the `parcel-volume-forecast` repository. It is written for technical leads and quality architects who need a precise, repo-level understanding of the model pipeline, governance artifacts, and test contracts.

## 1. EXECUTIVE ARCHITECTURAL SUMMARY

### Core objective
This repository is a focused, Databricks-first delivery scaffold for the `Multi Client Forecast IB Uplift Analysis` use case. Its primary technical objective is to turn the notebook-originated uplift forecasting workflow into a reproducible repository pipeline that:
- isolates transform and feature code into reusable modules,
- encapsulates training execution in a deterministic Python entrypoint,
- captures governance evidence at runtime, and
- aligns model delivery with CMMI Level 5 process metrics.

The repo is not a generic ML toolkit. It is a project-specific production scaffold whose purpose is to govern the lifecycle of a single XGBoost uplift forecasting model from data ingest through MLflow logging and job orchestration.

Production execution standard:
- Production runs are triggered by Databricks Job schedules configured inside Databricks, not notebook-only execution.
- Local runs are preflight checks and are not production verification evidence.
- Runtime source parameters (for example `source_table`) are resolved in orchestration with precedence `CLI -> env -> config default`.

### Bridge between software testing and ML orchestration
In this repo, quality engineering and ML model orchestration intersect along the following lines:
- `tests/` hold the equivalent of software assertions that validate data and process contracts before any model promotion.
- `src/training/train_xgboost.py` is the runtime executable that behaves like a production application entrypoint.
- `MLflow` operates as the experiment-tracking analog of CI build history, where run IDs and metrics serve the same role as Jenkins build numbers and test results.
- `jobs/train_job.yaml` defines the scheduled Databricks orchestration, so the repo’s training workflow is not manual exploration but an operationalized pipeline.

This makes the repo a hybrid between traditional Pytest-based QA and real ML pipeline delivery.

## 1.5 PHASE 0 CMMI LOCAL FRAMEWORK MAP (FOR JUNIOR ENGINEERS)

### Business problem we are solving
Deploy a reliable parcel volume uplift forecasting model with reproducible, governed training that can be audited and rolled back if needed.

### One concrete scenario
Every Monday, the Databricks job runs automatically from `jobs/train_job.yaml`, executes `src/training/train_xgboost.py` with latest data from `/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv`, logs metrics to MLflow, and decides: **promote or reject**. A rejection blocks promotion if `test_smape_target > 15%` OR any CMMI process gate fails.

Trigger ownership rule:
- Databricks schedules are the Phase 0 production trigger path.
- UI-triggered runs are for diagnostics and controlled troubleshooting only.

### How the framework flows (end-to-end)

The table below uses a representative test example for each step. In other words, the “Test file” column points to the relevant test module or the most representative test case for that stage, not to a single isolated assertion in every case.

Important: this is a conceptual map, not a literal runtime sequence where the training job calls pytest before starting. In this repo, the unit tests are normally run separately during local validation or CI. If they pass, the Databricks workflow can start. During the actual job run, the training script itself performs runtime data validation before training begins. So the test column shows the safety net for that stage, while the training script controls the live execution flow.

| Step | What happens | Technical file | Governance file | Representative test(s) | Output |
|---|---|---|---|---|---|
| 1. Trigger | Databricks schedule or CLI call | `jobs/train_job.yaml` | `docs/project/runbook.md` | — | Job run starts |
| 2. Load & validate data | Read CSV, check for nulls, negatives, baseline > 0 | `src/data/load_training_data.py`, `src/training/train_xgboost.py` (validation) | — | `tests/test_training.py` (for example `test_validate_input_dataframe_rejects_bad_values`) | Clean training data |
| 3. Transform features | Build cyclical time features, compute uplift target | `src/features/time_features.py`, `src/features/target_transform.py` | — | `tests/test_target_transform.py` (for example `test_target_transform_roundtrip`) | Transformed features |
| 4. Split & train | Split into train/val/test, train XGBoost | `src/training/train_xgboost.py` (split + train) | — | `tests/test_training.py` (for example `test_split_train_val_test_success`) | Trained model |
| 5. Evaluate | Compute SMAPE on val and test | `src/evaluation/metrics.py`, `src/training/train_xgboost.py` | — | — | `test_smape_target`, `val_smape_target` |
| 6. Compute process metrics | Measure baseline speed (≤2h), evaluation speed (≤24h), artifact completeness | `src/governance/cmmi_l5_metrics.py` | — | `tests/test_cmmi_l5_metrics.py` | CMMI gate flags |
| 7. Log to MLflow | Record core metrics, params, model artifact, run ID | `src/training/train_xgboost.py` | — | — | MLflow run record |
| 8. Generate run report artifacts | Build and publish `run_summary.json` and `run_summary.html` | `src/reporting/training_report.py`, `src/training/train_xgboost.py` | `docs/project/phase0_leadership_summary.md` | — | Structured run report |
| 9. Decision gate | Check: SMAPE pass AND CMMI gates pass? | `src/governance/cmmi_l5_metrics.py` | `docs/project/phase0_leadership_summary.md` | — | **Pass / Reject** |
| 10. Report status | Record go/no-go decision and rationale | — | `docs/project/decision_log.md` | — | Auditable decision |
| 11. Optional: Dashboard | Query process metrics for trend analysis | — | `sql/cmmi_l5_process_metrics.sql` | — | Governance KPI view |

### Files at a glance

**Technical core (where the work happens):**
- `src/data/` — data loading and validation
- `src/features/` — transforms (time features, uplift target)
- `src/training/` — training entrypoint and MLflow logging
- `src/evaluation/` — metrics (SMAPE)
- `jobs/` — production workflow definition

**Governance layer (how we ensure quality):**
- `src/governance/` — CMMI gate logic and process KPIs
- `sql/` — governance KPI view for dashboards
- `docs/project/runbook.md` — how to trigger and validate
- `docs/project/decision_log.md` — decisions and rationale
- `docs/project/phase*_leadership_summary.md` — phase status and go/no-go

**Safety net (tests that protect against regressions):**
- `tests/test_target_transform.py` — ensures uplift target round-trips correctly
- `tests/test_training.py` — ensures data validation and split logic work
- `tests/test_cmmi_l5_metrics.py` — ensures gate logic is stable

### Key takeaways for junior engineers

1. **Flow is deterministic:** same input CSV + code = same model and metrics every time.
2. **Promotion is gated:** a run only becomes production if SMAPE passes AND process gates pass.
3. **Every gate has a test:** transform, training split, gate logic — all have unit tests.
4. **Auditability is built in:** MLflow run ID, metrics, CMMI evidence, and decision are all logged.
5. **Governance is measurable:** not manual reviews, but automated gates with thresholds (SMAPE ≤ 15%, baseline speed ≤ 2h, etc.).

### How to debug if a run fails

| Symptom | Where to check | What to look for |
|---|---|---|
| Data validation error | `src/training/train_xgboost.py` validation block | Null values, negative actuals, non-positive baseline |
| Transform test fails | `tests/test_target_transform.py` | Round-trip tolerance or NaN/inf values |
| SMAPE is high | `src/evaluation/metrics.py`, MLflow run record | Check `val_smape_target` vs threshold (15%) |
| CMMI gate fails | `src/governance/cmmi_l5_metrics.py`, thresholds | Check `baseline_speed_pass`, `evaluation_speed_pass`, `artifact_completeness_pass` |
| Split test fails | `tests/test_training.py` | Check data size or date ordering |

---

## 2. CODESPACE & REPOSITORY ANATOMY (THE MAP)

### Folder tree
```
parcel-volume-forecast/
├── .github/
│   └── copilot-instructions.md
├── data/
│   └── multi_client_ib_uplift.csv
├── docs/
│   ├── ai-governance/
│   │   ├── bias_risk_assessment.md
│   │   ├── databricks_model_lineage.md
│   │   ├── model_card.md
│   │   └── steering/
│   │       └── steering.md
│   ├── archive/
│   │   └── ... archived generic ML governance docs ...
│   └── project/
│       ├── decision_log.md
│       ├── phase1_leadership_summary.md
│       ├── repository_structure_cmmi_l5_guide.md
│       ├── runbook.md
│       └── technical_onboarding.md
├── jobs/
│   └── train_job.yaml
├── mlruns_phase1/
│   └── ... local MLflow run metadata ...
├── notebooks/
│   └── README.md
├── PROJECT_SPEC.md
├── README.md
├── requirements-dev.txt
├── sql/
│   ├── cmmi_l5_process_metrics.sql
│   └── serving_forecast_view.sql
├── src/
│   ├── data/
│   │   └── load_training_data.py
│   ├── evaluation/
│   │   └── metrics.py
│   ├── features/
│   │   ├── target_transform.py
│   │   └── time_features.py
│   ├── governance/
│   │   └── cmmi_l5_metrics.py
│   └── training/
│       └── train_xgboost.py
├── tests/
│   ├── test_cmmi_l5_metrics.py
│   ├── test_target_transform.py
│   └── test_training.py
└── workflow/
    └── requirements/
        ├── 2026-06-23_phase-0-migration-mapping.md
        ├── 2026-06-23_phase-1-scaffold-quick-win.md
        └── 2026-06-24_stagewise-workflow-report.md
```

## 3. DOMAIN GLOSSARY FOR JUNIOR ENGINEERS

This glossary defines the key terms used by the repository and the Databricks/ML workflow.

- **Databricks Workflow**: An orchestration definition in Databricks that runs one or more tasks (Python scripts, notebooks, etc.) according to a schedule or trigger.
- **Spark Python Task**: A Databricks job task that executes a Python file on a Spark cluster. In this repo, `src/training/train_xgboost.py` is run as a Spark Python task.
- **Notebook Task**: A Databricks job task that executes a notebook. It provides notebook UI execution and cell-by-cell visibility.
- **Python entrypoint**: The main script that starts the training pipeline and handles parameters. Here it is `src/training/train_xgboost.py`.
- **MLflow experiment**: A logical group for related runs. It keeps runs together under the same experiment name.
- **MLflow run**: A single execution of the training pipeline. It stores metrics, parameters, tags, and artifacts for that execution.
- **Metric**: A numeric value logged during a run, such as `test_smape_target`. Metrics are used to compare model performance.
- **Parameter**: A configuration value logged with a run, such as `dataset_version` or `feature_count`.
- **Artifact**: A file or model saved during a run, such as a trained model, JSON summary, or notebook output.
- **CMMI Level 5**: A process maturity framework. In this repo, it means capturing governance metrics and making process performance measurable.
- **Gate**: A pass/fail checkpoint in the workflow, such as reproducibility, quality, or documentation gates.
- **Target transform**: The conversion that turns raw actual and baseline values into the model target for uplift forecasting.
- **Uplift modeling**: Predicting incremental change relative to a baseline rather than predicting an absolute value.
- **Stagewise reporting**: Breaking the pipeline into stages and reporting the status of each stage.
- **DBFS**: Databricks File System. A storage layer used by Databricks where training data and artifacts can be stored.
- **Governance evidence**: Logged artifacts, metrics, and documents that prove the run followed required process and quality controls.

### Folder and file responsibilities

- `.github/copilot-instructions.md`
  - Defines the repo-specific AI guidance and behavioral rules for the Copilot assistant.
  - Signals which steering documents are authoritative for code generation and governance.

- `data/multi_client_ib_uplift.csv`
  - Local training data extract used for development and validation.
  - Provides a concrete dataset to exercise the training entrypoint in repo-scope tests and local runs.

- `docs/ai-governance/bias_risk_assessment.md`
  - Captures model bias, risk, and ethics considerations specific to the uplift forecasting model.
  - Supports governance reviews by documenting known limitations and mitigation strategies.

- `docs/ai-governance/databricks_model_lineage.md`
  - Records model lineage from notebook to repository code and to MLflow/Unity Catalog.
  - Serves as the traceability artifact needed for audit and rollback.

- `docs/ai-governance/model_card.md`
  - Formal model card documenting intended use, features, target, evaluation, and governance controls.
  - Acts as the project-specific AI governance artifact for promotion.

- `docs/ai-governance/steering/steering.md`
  - The behavioral and governance steering document for this repo.
  - Describes process rules, ML context, and CMMI-aligned controls.

- `docs/project/decision_log.md`
  - Operational decision record for project-level choices.
  - Useful for retrospective analysis and evidence of decision rationale.

- `docs/project/phase1_leadership_summary.md`
  - Executive summary artifact for Phase 1 delivery status.
  - Captures phase scope, outcomes, and governance evidence.

- `docs/project/repository_structure_cmmi_l5_guide.md`
  - Project-specific architecture guide that maps repo structure to CMMI L5 controls.
  - Helps newcomers understand how folders correspond to governance artifacts.

- `docs/project/runbook.md`
  - Operational runbook for local validation and Databricks execution.
  - Contains training trigger, validation checklist, and model promotion guidance.

- `jobs/train_job.yaml`
  - Databricks workflow definition for scheduled training.
  - Specifies the Python entrypoint, cluster binding, input CSV path, experiment name, and schedule.

- `mlruns_phase1/`
  - Local MLflow storage for example runs and artifacts.
  - Demonstrates the structure of run metadata, metrics, params, tags, and model artifact outputs.

- `notebooks/README.md`
  - Notebook folder guide for exploratory work.
  - Indicates that notebooks are for discovery, not production logic.

- `PROJECT_SPEC.md`
  - High-level repository mission and Phase 1 scope document.
  - Provides the project objective, folder mapping, and CMMI controls.

- `README.md`
  - General onboarding and best practices guide for the repo.
  - Describes the overall delivery mode and why this repo exists.

- `requirements-dev.txt`
  - Dev dependency pin list for local testing and validation.
  - Contains MLflow, numpy, pandas, xgboost, pytest, pyarrow, and pyspark.

- `sql/cmmi_l5_process_metrics.sql`
  - SQL view defining process-quality KPIs for governance reporting.
  - Exposes CMMI metrics in SQL for downstream BI or audit queries.

- `sql/serving_forecast_view.sql`
  - Consumer facing SQL view for the latest forecast per client and event date.
  - Enforces deduplication semantics for scored output.

- `src/data/load_training_data.py`
  - Spark-based data loading and client filtering contract.
  - Encapsulates training dataset selection and low-volume client filtering.

- `src/evaluation/metrics.py`
  - Defines model evaluation metric `smape()`.
  - Provides a single source of truth for how forecast error is measured.

- `src/features/target_transform.py`
  - Target transform contract for uplift modeling.
  - Implements forward and inverse transforms with validation.

- `src/features/time_features.py`
  - Adds cyclical time encodings used by the uplift model.
  - Produces deterministic time-based feature columns.

- `src/governance/cmmi_l5_metrics.py`
  - Process governance metric definitions and gate status logic.
  - Converts run timing and artifact flags into CMMI pass/fail booleans.

- `src/training/train_xgboost.py`
  - Main training pipeline entrypoint.
  - Loads data, applies transforms, trains XGBoost, evaluates, and logs to MLflow.

- `tests/test_target_transform.py`
  - Round-trip contract test for the uplift target transform.
  - Ensures the transform and inverse transform are lossless.

- `tests/test_cmmi_l5_metrics.py`
  - Automated gate test for CMMI process metrics.
  - Ensures governance metrics and promotion-rate logic remain stable.

- `tests/test_training.py`
  - Validation tests for training helper functions and split logic.
  - Confirms feature inference, input validation, and time-window partitioning.

- `workflow/requirements/*.md`
  - Approved requirements artifacts for the repo’s delivery phases.
  - Capture the scope and evidence of this repository’s implementation decisions.

## 3. THE CONTINUOUS TRAINING (CT) LIFE CYCLE & DATABRICKS WORKFLOW

### Design for automated scheduled execution
The repository is designed around a deterministic training entrypoint, not notebook state. The key execution path is:
1. `jobs/train_job.yaml` defines the Databricks Workflow task.
2. The task executes `../src/training/train_xgboost.py` on a cluster.
3. The training script reads runtime parameters and a CSV input.
4. It applies feature transforms, trains XGBoost, evaluates holdout data, and logs everything to MLflow.

This creates a continuous training pipeline because the same code can run locally for validation and in Databricks for scheduled production retraining.

### Parameter flow
- Runtime configuration enters through `argparse` in `src/training/train_xgboost.py`.
- The script currently expects:
  - `--input-csv`
  - `--experiment`
  - `--dataset-version`
- In Databricks, these values are provided by the job task definition in `jobs/train_job.yaml`.
- There is no `dbutils` call in the source code today; the repo uses the job parameter mechanism as its dynamic runtime configuration model.

### MLflow integration as CI/CD history
MLflow is used as the execution history and governance record. It maps to CI/CD concepts as follows:
- `mlflow.set_experiment(experiment_name)` is equivalent to selecting the CI pipeline or logical job name.
- `mlflow.start_run()` is equivalent to a single build/run execution.
- `mlflow.log_param()` is equivalent to build metadata and environment configuration.
- `mlflow.log_metric()` is equivalent to test results or performance assertions.
- `mlflow.xgboost.log_model()` is equivalent to archiving a build artifact for deployment.

This means the repository treats MLflow as the canonical build history store for model training runs.

### Workflow output and serving expectations
- Trained models are recorded in MLflow and can be registered into Unity Catalog.
- The downstream serving contract is defined by `sql/serving_forecast_view.sql`, which expects scored output rows in a prediction table and exposes the latest prediction per `client_name` and `event_date`.
- This repo therefore separates training from serving, with the SQL artifact serving as the downstream consumption contract.

## 4. THE QUALITY GATES & DATA CONTRACTS EXPLAINED

### `tests/test_target_transform.py`
This test file validates the transform/inverse transform contract for uplift modeling.

#### Technical mechanics
- `build_uplift_target(df)` computes `log(actual_volume / rolling_4w_median)`.
- `invert_uplift_target(log_uplift, baseline)` computes `exp(log_uplift) * baseline`.
- The test asserts `reconstructed == actual_volume` within numeric tolerance.

#### Why it matters
- It guarantees the target transformation is reversible and lossless for absolute volume prediction.
- It prevents silent target-contract regression that would break inference and reporting.
- In QA terms, it is a contract test that verifies encoding/decoding symmetry.

### `tests/test_cmmi_l5_metrics.py`
This test file validates the governance gate logic encoded in `src/governance/cmmi_l5_metrics.py`.

#### Technical mechanics
- Creates example `CmmiRunRecord` objects with known timestamps and flags.
- Evaluates `cmmi_l5_gate_status()` for baseline speed, evaluation speed, and artifact completeness.
- Verifies `promotion_rate()` computes the correct ratio of promoted runs.

#### Why it matters
- It codifies process governance as an automated test rather than a manual review step.
- It prevents regression in the repo’s process-quality gate logic.
- This is the explicit TMMi/CMMI Level 5 parallel: automated policy enforcement, where policy is defined in code and validated by tests.

### Data contract mechanics in the training pipeline
The repo enforces data contracts at multiple levels:
- `src/training/train_xgboost.py` validates required columns, null values, negative actuals, non-positive baselines, and empty CSVs.
- `src/features/target_transform.py` validates input shape and value semantics before computing the uplift target.
- `src/features/time_features.py` ensures deterministic cyclical encoding for date features.
- `tests/test_training.py` verifies that the time-based train/val/test split behaves correctly and rejects insufficient data.

These controls turn the training code into a guarded pipeline that is both testable and governance-ready.

## Summary
This repository is a disciplined ML delivery scaffold that bridges:
- **QA automation** via `tests/`, data contract validation, and process gate assertions,
- **ML orchestration** via `src/training/train_xgboost.py`, Databricks `jobs/train_job.yaml`, and MLflow experiment logging,
- **Governance** via `docs/ai-governance/`, the `cmmi_l5_metrics` engine, and SQL KPI views.

It is structured to support safe promotion of a model from exploratory notebook proof-of-concept into a repeatable and auditable training workflow.
