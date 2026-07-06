# Parcel Volume Forecast Framework

Lead ML architect reference for the production-grade training framework used to forecast multi-client parcel volume uplift.

## Framework Intent

This repository implements a governed ML framework that balances four goals:

1. Forecast quality with robust time-aware model training.
2. Safe data handling through explicit refinery contracts.
3. Operational reliability in Databricks and local environments.
4. Auditability via MLflow evidence and CMMI L5 process metrics.

## Architecture Overview

The framework is organized as an end-to-end pipeline with explicit control points:

1. Source selection and ingestion
- Supports CSV and Unity Catalog table input.
- Runtime source resolution follows precedence: CLI input, environment variable, central config default.

2. Stage 2 data refinery contract
- Enforces required column mapping from raw or normalized schemas.
- Applies lookback window filtering.
- Enforces non-null checks for date, actual, baseline, and target.
- Enforces baseline volume floor.

3. Stage 3 volumetric guardrail
- Evaluates filtered volume against approved operational thresholds.
- Returns one of: nominal pass, approved deviation warning, or critical failure.
- Prevents model training when data starvation or severe quality loss is detected.

4. Feature, target, split, and model training
- Builds cyclical time features and uplift target.
- Uses time-aware train/validation/test splits.
- Trains XGBoost with centralized hyperparameters.

5. Evaluation and governance evidence
- Logs metrics and artifacts to MLflow.
- Applies quality and process gates (SMAPE and CMMI metrics).
- Emits structured run reports for operational review.

## Repository Structure

- `src/config.py`: central runtime and governance defaults.
- `src/training/train_xgboost.py`: production training entrypoint.
- `src/training/refinery.py`: Stage 2/Stage 3 data contract logic.
- `src/features/`: feature and target transformations.
- `src/evaluation/`: model metrics.
- `src/governance/`: CMMI L5 metric and gate evaluation.
- `tests/`: refinery, training, features, and governance tests.
- `docs/project/operations/`: runbook and Databricks troubleshooting references.
- `jobs/`: job definitions and job reset payloads.
- `sql/`: operational SQL and process metric views.

## Recent Data-Handling Enhancements

The latest framework updates include:

1. Schema-compatible live-table intake
- Added alias resolution for raw and normalized schemas.
- Supports alternate live-table date column naming, including `DATE_DATE`.

2. Stage 3 starvation prevention
- Guardrail now blocks training when filtered rows are below the minimum volume envelope.
- This converts silent degraded training into explicit, actionable failure.

3. SQL parity pre-check pattern
- Operational docs now include SQL checks that mirror Stage 2 predicates.
- This allows fast validation of expected row volume before triggering expensive training runs.

4. Local debug artifact isolation
- Local troubleshooting scripts and outputs are isolated under `local-debug/`.
- These artifacts are excluded from Git by policy.

## Run Modes

1. Local smoke validation
- Fast functional verification with CSV input.
- Recommended before changing job config or promoting commits.

2. Databricks governed run
- Production path for live-table execution and MLflow evidence.
- Uses the same repository entrypoint with runtime parameterization.

## Quality and Governance Gates

The framework enforces two classes of controls:

1. Model quality gate
- Maximum allowed test SMAPE threshold.

2. Data and process governance gates
- Stage 2 and Stage 3 data contract checks.
- CMMI timing and artifact completeness checks.

## Quick Start

### 1) Install dependencies

```bash
pip install -r requirements-dev.txt
```

### 2) Run tests

```bash
python -m pytest
```

### 3) Local smoke run

```bash
python -m src.training.train_xgboost --input-csv data/multi_client_ib_uplift.csv --experiment parcel-volume-forecast-local-smoke --dataset-version v1 --run-mode debug
```

### 4) Generate test report artifacts

```bash
python scripts/run_tests_with_report.py
```

## Databricks Operations

Use the operational guides for current job wiring and run diagnostics:

- `docs/project/operations/runbook.md`
- `docs/project/operations/databricks_debug_reference.md`

These documents are the source of truth for:

1. Active production job configuration.
2. Trigger methods (UI, CLI, REST, SDK).
3. Stage 3 guardrail troubleshooting.
4. SQL parity checks for pre-run data validation.

## Design Principles

1. Configuration over hardcoding.
2. Fail fast on data contract violations.
3. Keep governance evidence first-class.
4. Preserve production parity between local and Databricks execution.
5. Keep debug convenience isolated from governed artifacts.

## Ownership

Model owner: Central Analytics

For roadmap, operating decisions, and governance context, see the documentation under `docs/`.
