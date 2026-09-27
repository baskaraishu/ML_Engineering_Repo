# AI Governance - Databricks Model Lineage
# Model: XGBoost_MultiClient_Forecast_IB_Uplift_Analysis
# Phase: 1 (MVP — source notebook identified, local repo scaffold created)

---

## 1. Source Notebook (Databricks Workspace)

| Property | Value |
|---|---|
| Notebook path | /Users/aishwarya.lakshmi@hermes-europe.co.uk/Multi Client Forecast IB Uplift Analysis |
| Workspace | https://dbc-b3d61392-d9a7.cloud.databricks.com |
| Language | Python |
| Last modified | 2026-06-21 |
| Notebook status | Original Genie-assisted exploration notebook |

---

## 2. Local Repo Mapping (Phase 1 Promotion)

| Notebook section | Local repo file | Status |
|---|---|---|
| Data loading + client filter | src/data/load_training_data.py | Done |
| Time cyclical features | src/features/time_features.py | Done |
| Target log-uplift transform | src/features/target_transform.py | Done |
| XGBoost train + MLflow logging | src/training/train_xgboost.py | Done |
| SMAPE metric | src/evaluation/metrics.py | Done |
| CMMI process KPIs | src/governance/cmmi_l5_metrics.py | Done |
| Optuna hyperparameter tuning | src/training/tune_optuna.py | Phase 2 |
| SHAP explainability | src/evaluation/explainability.py | Phase 2 |
| Batch inference | src/inference/batch_predict.py | Phase 2 |
| Per-client accuracy report | src/evaluation/client_performance.py | Phase 2 |

---

## 3. Unity Catalog Model Registry

| Property | Value |
|---|---|
| Registered model name | XGBoost_MultiClient_Forecast_IB_Uplift_Analysis |
| Registry location | Unity Catalog (evri_datalakehouse_prod_catalog) |
| Promotion flow | MLflow Pending → Approved → Production |
| Champion criteria | SMAPE degradation ≤ 3% vs current champion |

---

## 4. How to Pull a Specific Model Version Locally

```python
import mlflow

mlflow.set_tracking_uri("databricks")

model_name = "XGBoost_MultiClient_Forecast_IB_Uplift_Analysis"
model_version = "latest"  # or specific version integer

model = mlflow.xgboost.load_model(f"models:/{model_name}/{model_version}")
```

---

## 5. Lineage Chain (End to End)

```
fcast_multi_client_data_build_champion_IB_uplift (analytics_sandbox)
  -> src/data/load_training_data.py  (client filter, volume gate)
  -> src/features/time_features.py   (cyclical encodings)
  -> src/features/target_transform.py (log-uplift target)
  -> src/training/train_xgboost.py   (train + MLflow log)
  -> Unity Catalog Model Registry    (versioned, governed)
  -> jobs/train_job.yaml             (scheduled execution)
  -> sql/serving_forecast_view.sql   (consumer layer)
  -> Power App / Power BI            (end user)
```
