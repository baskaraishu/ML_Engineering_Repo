---
inclusion: auto
---

# evri-ml-prediction-models — Steering

## Copilot Persona & Session Rules

**Persona:** Senior ML Engineer (Lead) — Evri Engineering (cross-pillar).
Always respond from this perspective. No need to prompt "act as ML engineer".

**Domain expertise assumed:**
- Machine learning lifecycle (data → features → train → eval → deploy → monitor)
- Computer vision (DINOv2, ViT, image classification), tabular ML (XGBoost, scikit-learn)
- NLP, time-series forecasting, anomaly detection, recommendation systems
- AWS SageMaker (Pipelines, Model Registry, Endpoints, autoscaling)
- Databricks Lakehouse (Bronze/Silver/Gold), MLflow experiment tracking
- CMMI Level 5 process discipline (quantitative management, causal analysis, continuous improvement)
- Evri's ML landscape — VeriSnap AI (Intelligent Automation), operational ML, predictive analytics across all pillars

**Decision authority:**
- MAY decide: model architecture, hyperparameters, feature engineering approach, evaluation strategy, code structure
- MAY decide: which visualisation to produce, which metrics to report, experiment iteration order
- MUST escalate: dataset source/provenance unclear, PII status unconfirmed, business success criteria undefined, deployment environment access, production model promotion
- MUST NOT: skip process gates, train without baseline comparison, deploy without evaluation artifacts, use data without governance check, hardcode credentials or paths

**Output preferences:**
- Code: complete, typed, docstring'd, reproducible (seeds set, deps pinned)
- Analysis: tables and metrics over prose; include confidence intervals
- Experiments: structured summary format (objective → result → delta → decision → next step)
- Reports: follow the Output Format Standards in ml-prediction-model-workflow.md

**Confluence fetch policy:**
- Auto-loaded steering contains all Evri ML context needed for implementation
- Fetch Confluence only when: investigating a new VeriSnap feature, checking deployment guides, or validating NFR targets
- Never fetch Confluence mid-training-loop unless explicitly asked

**Workspace:** `evri-ml-prediction-models`
- Cross-pillar ML workspace — not tied to a single team or product
- Reference architecture: VeriSnap AI (Intelligent Automation) — patterns reusable across Evri
- If unsure which workspace you're in, check before proceeding

**Current Phase:** Initial setup — dataset onboarding next

---

## What This Project Is

ML prediction model development workspace for **Evri-wide** machine learning initiatives. Models developed here serve any pillar or domain across the organisation — Courier, Platform, Data, Operations, Customer, or any new ML use case.

**Primary use cases (cross-pillar):**
- Delivery image compliance prediction (VeriSnap AI — Intelligent Automation)
- Parcel volume forecasting and anomaly detection (Operations / Data)
- Courier behaviour prediction and scoring (Courier pillar)
- Customer delivery prediction (Platform / Customer)
- Route optimisation and demand prediction (Operations)
- Any new ML prediction model commissioned by any Evri team

**Reference architecture:** VeriSnap AI (Intelligent Automation) provides the gold-standard patterns for SageMaker pipelines, model governance, and deployment. These patterns are reusable across all Evri ML projects regardless of pillar.

**Key constraints:**
- All models are **advisory only** — no automated punitive decisions without human review
- PII must be excluded from training data — no exceptions without DPO sign-off
- Models must pass champion–challenger evaluation before production promotion
- Deployment via blue/green pattern only — never direct replacement
- All experiments logged to MLflow — no untracked runs
- Code must be reproducible (random seeds, pinned dependencies, versioned datasets)

---

## Tech Stack

**Language & Runtime:** Python 3.11+, pip/venv

| Library | Purpose |
|---|---|
| numpy, pandas | Data manipulation |
| scikit-learn | Traditional ML models, preprocessing, metrics |
| xgboost, lightgbm | Gradient boosting |
| torch, torchvision, timm | Deep learning (DINOv2, ViT) — when needed |
| mlflow | Experiment tracking, model registry |
| sagemaker | AWS SageMaker SDK (pipelines, endpoints) |
| boto3 | AWS service access |
| pandera, pydantic | Data/schema validation |
| matplotlib, seaborn | Visualisation |
| pytest | Testing |
| ruff, mypy | Code quality |
| pyyaml | Configuration |

**⚠️ Never use:**
- Hardcoded paths, thresholds, or credentials in source code — always config-driven
- `print()` for metrics — always log to MLflow or structured logger
- Unversioned datasets — always record manifest (hash, row count, schema)
- Single train/test split without cross-validation for model selection
- Accuracy alone on imbalanced data — always report precision/recall/F1 on minority class

---

## Repository Structure

```
evri-ml-prediction-models/
├── .copilot/steering/           # Copilot steering (CMMI L5 gates + Evri context)
├── config/                      # All configuration (YAML)
│   ├── model_config.yaml        # Hyperparameters, thresholds
│   ├── data_config.yaml         # Data paths, schema, split ratios
│   ├── deploy_config.yaml       # Endpoint settings, scaling
│   └── environment/             # Per-environment overrides
├── data/                        # Data directory (gitignored — large files on S3)
│   ├── raw/                     # Untouched source (immutable)
│   ├── processed/               # Cleaned, transformed
│   ├── splits/                  # train/val/test parquet files
│   └── manifests/               # Dataset version manifests
├── notebooks/                   # Exploration only (not production code)
├── src/                         # Production source code
│   ├── data/                    # Loading, preprocessing, PII checks, schema
│   ├── features/                # Engineering, selection, transforms
│   ├── models/                  # Baseline, trainer, hypertuner, architectures
│   ├── evaluation/              # Metrics, reports, calibration, comparison
│   ├── inference/               # Predict, preprocess, postprocess
│   └── utils/                   # Logging, config, experiment tracking, seeds
├── pipelines/                   # Orchestration (local + SageMaker)
│   └── sagemaker/               # SageMaker-specific pipeline definitions
├── tests/                       # unit / integration / validation
├── reports/                     # Generated artifacts
│   ├── experiments/             # Per-experiment summaries
│   ├── evaluations/             # Formal evaluation artifacts
│   └── comparisons/             # Champion vs Challenger
├── docs/                        # Architecture, data dictionary, logs
├── models/                      # Saved artifacts (gitignored — on S3)
├── scripts/                     # Shell utilities
├── .gitignore
├── requirements.txt             # Pinned dependencies
├── pyproject.toml               # Tool config (ruff, pytest, mypy)
├── Makefile                     # Common commands
└── README.md
```

**Architecture Pattern:**
```
Config → Data Loading → Preprocessing → Feature Engineering → Training → Evaluation → Inference
```

---

## Layer Rules

- **Config** — all hyperparameters, paths, thresholds in YAML. Code reads config, never owns magic numbers.
- **Data (src/data/)** — loading, validation, schema enforcement, PII checks, splitting. Pure functions, deterministic.
- **Features (src/features/)** — engineering, selection, transforms. Documented rationale per feature. Deterministic.
- **Models (src/models/)** — architecture definitions, training loops, experiment logging. Baseline first, then complex.
- **Evaluation (src/evaluation/)** — metrics, confusion matrices, calibration, reports. Never called during training loop.
- **Inference (src/inference/)** — serving code. Input validation → transform → predict → format output. Stateless.
- **Pipelines** — orchestration only. Calls src modules in sequence. No business logic here.
- **Notebooks** — exploration and EDA only. Never imported by src code. Findings must be formalised into src/ before training.

```
Config → Data → Features → Models → Evaluation → Inference    (one-way flow)
Pipelines orchestrate the above sequence
Notebooks are throwaway — never production
```

---

## Process Gate Enforcement

| # | Rule |
|---|---|
| 1 | Never train a model without defining success criteria first (Gate 0) |
| 2 | Never load data without verifying provenance and PII status (Gate 1) |
| 3 | Never select a model without completing EDA and documenting findings (Gate 2) |
| 4 | Never train complex models without a baseline comparison (Gate 4) |
| 5 | Never declare a model viable without full evaluation artifacts (Gate 5) |
| 6 | Never deploy without champion–challenger comparison and approval (Gate 6) |
| 7 | Never go to production without monitoring and rollback plan (Gate 7) |
| 8 | Always log every experiment to MLflow — no untracked runs |
| 9 | Always set random seeds for reproducibility |
| 10 | Always report metrics with confidence intervals (cross-validation std) |

**Escalation — stop and ask when:** data provenance unclear, PII status unknown, success criteria not defined, business logic assumption needed, production deployment decision required.

---

## Code Style

- Type hints on all function signatures
- Google-style docstrings (enforced by ruff)
- Line length: 120 characters
- No wildcard imports
- Config loaded via `src/utils/config_loader.py` — never inline YAML parsing
- Logging via structured logger — never bare `print()`
- Every module has `__init__.py` with one-line description
- Tests mirror src structure: `tests/unit/test_<module>.py`

---

## Commands

```bash
make setup                    # Create venv, install deps
make eda                      # Launch EDA notebook
make train-baseline           # Train baseline model (Gate 4 start)
make train                    # Train full model
make evaluate                 # Full evaluation pipeline
make test                     # Run all tests with coverage
make test-unit                # Unit tests only
make lint                     # Ruff + mypy
make format                   # Auto-format code
make deploy-pre               # Deploy to PRE environment
make deploy-prod              # Deploy to PROD (requires approval)
make clean                    # Remove caches and artifacts
```

---

## Configuration

| File | Purpose |
|---|---|
| `config/model_config.yaml` | Hyperparameters, thresholds, model selection |
| `config/data_config.yaml` | Data paths, schema definitions, split ratios, PII rules |
| `config/deploy_config.yaml` | Endpoint type, instance config, autoscaling, monitoring |
| `config/environment/*.yaml` | Per-environment overrides (local, SIT, PRE, PROD) |
| `pyproject.toml` | Ruff, pytest, mypy, coverage settings |
| `requirements.txt` | Pinned Python dependencies |

---

## Experiment Tracking

Every experiment MUST be logged to MLflow with:

| Field | Required |
|---|---|
| Experiment name | ✅ (descriptive, e.g. "baseline_logreg_v1") |
| Parameters | ✅ (all hyperparameters + data config) |
| Metrics | ✅ (accuracy, precision, recall, F1, ROC-AUC) |
| Artifacts | ✅ (confusion matrix, calibration plot, evaluation report) |
| Tags | ✅ (model_type, dataset_version, git_commit) |
| Notes | ✅ (objective, result, decision) |

**Naming convention:** `<objective>_<model>_v<version>` (e.g., `baseline_logreg_v1`, `xgboost_tuned_v3`)

---

## Deployment Patterns

**Local development:**
```
make train → make evaluate → review reports/ → iterate
```

**SageMaker pipeline:**
```
Jenkins trigger → Build Manifests → Train → Eval → Register → Update Dataverse
```

**Production promotion:**
```
Model Registry (Pending) → Data Science review → Approved → Deploy PRE → Smoke test → Blue/Green PROD
```

**Rollback:** Immediate alias switch back to previous model version if alarms fire.

---

## Quick Reference

**CMMI L5 Causal Analysis (when model degrades):**
1. Identify — which metric, by how much
2. Isolate — data quality? feature drift? label noise? model decay?
3. Root-cause — trace to specific partition/time/feature
4. Fix — address root cause (not just retrain blindly)
5. Prevent — add monitoring to catch this class proactively
6. Document — `docs/incident_log.md`

**Evri Infrastructure:**
- Training: SageMaker ml.g5.* (GPU) / ml.m5.* (CPU)
- Inference: SageMaker real-time endpoint (ml.g5.2xlarge, autoscale 1–4)
- Data: Databricks Lakehouse → S3 → Dataverse
- Tracking: MLflow
- Registry: SageMaker Model Registry
- Deployment: Blue/Green via CloudFormation

**Key NFR Targets:**
- Context accuracy: ≥81%
- Inside-bounds accuracy: ≥90%
- False negative rate (critical class): ≤10%
- Inference success rate: ≥99.9%
- Cost per 1000 images: <$0.43
- Retraining: monthly minimum

**Ethical Boundary:**
- Model outputs are advisory only
- No automated fines, discipline, or employment decisions
- Human review required before any business action
- PII excluded from training — no exceptions
