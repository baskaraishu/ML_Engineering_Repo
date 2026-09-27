# Parcel Volume Forecast

This repository contains a production-style forecasting pipeline for parcel volume uplift modeling. It is designed to be clear, testable, and reusable while keeping operational configuration separate from business logic.

## What is included

- Time-aware feature engineering
- Training/validation/test splits
- XGBoost regression modeling
- Data refinery and guardrail checks
- MLflow-friendly reporting hooks
- Unit tests covering the main pipeline logic

## Repository structure

- `src/` — core pipeline code
- `tests/` — regression and unit tests
- `data/` — example dataset used for local runs
- `requirements-dev.txt` — development dependencies

## Quick start

### Install dependencies

```bash
pip install -r requirements-dev.txt
```

### Run tests

```bash
python -m pytest
```

### Local smoke run

```bash
python -m src.training.train_xgboost --input-csv data/multi_client_ib_uplift.csv --experiment parcel-volume-forecast-local-smoke --dataset-version v1 --run-mode debug
```

## Notes

This repository is intentionally sanitized for public sharing. Any organization-specific infrastructure, cluster IDs, job IDs, or internal environment references should be replaced with placeholders before deployment to a shared or personal repo.
