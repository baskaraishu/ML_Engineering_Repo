# AI Governance - Model Card
# Model: XGBoost Multi-Client Forecast IB Uplift Analysis
# Databricks UC Registry: XGBoost_MultiClient_Forecast_IB_Uplift_Analysis
# Phase: 1 (MVP)

---

## 1. Model Identity

| Property | Value |
|---|---|
| Model name | XGBoost_MultiClient_Forecast_IB_Uplift_Analysis |
| Model type | Gradient-boosted regression (XGBRegressor) |
| Version tracked in | Databricks Unity Catalog Model Registry |
| MLflow experiment | /Shared/forecasting/parcel-volume-forecast |
| Source notebook | /Users/aishwarya.lakshmi@hermes-europe.co.uk/Multi Client Forecast IB Uplift Analysis |
| Promoted to local repo | Yes — src/training/train_xgboost.py |
| Owner | Central Analytics |

---

## 2. Intended Use

- Forecast daily inbound parcel volume uplift per client
- Input to network resource planning (Power App consumer)
- Advisory only — planners review and adjust outputs

## 3. Out of Scope

- Automated punitive or financial decisions without human review
- Clients with median daily volume ≤ 10 (excluded by design)

---

## 4. Training Data

| Property | Value |
|---|---|
| Source table | fcast_multi_client_data_build_champion_IB_uplift (analytics_sandbox) |
| Client scope | Clients present in champion model v35 only |
| Low-volume filter | Median daily volume > 10 |
| Split method | Time-based: train / 42-day val / 42-day holdout test |
| PII | No customer PII in training features |

---

## 5. Features

| Feature | Description |
|---|---|
| month_sin / month_cos | Cyclical month encoding |
| dow_sin / dow_cos | Cyclical day-of-week encoding |
| doy_sin / doy_cos | Cyclical day-of-year encoding |
| woy_sin / woy_cos | Cyclical week-of-year encoding |
| dom_sin / dom_cos | Cyclical day-of-month encoding |
| is_china | Business flag — China client |
| is_domestic | Business flag — domestic client |

## 6. Target Variable

log(actual_volume / rolling_4w_median)

Inverse transform applied during inference to return predicted absolute volume.

---

## 7. Evaluation

| Metric | Scope | Phase-1 target |
|---|---|---|
| SMAPE | All clients | Tracked per run in MLflow |
| SMAPE | Per-client | Logged in evaluation output |
| Accuracy tier | Top-100 clients | Excellent / Good / Moderate / Poor |
| Promotion gate | Test SMAPE degradation | ≤ 3% vs champion |

---

## 8. Known Limitations and Risks

- Calendar features do not capture exceptional events (strikes, peak disruptions)
- Client-level accuracy varies significantly across low/high-volume segments
- Uplift target assumes 4-week median is a stable baseline — volatile clients may drift
- Model has no built-in uncertainty quantification

---

## 9. CMMI L5 Governance Controls Applied

| Control | Status |
|---|---|
| Problem framing and success criteria defined | Yes |
| Dataset version recorded | Required per run |
| PII controls | Enforced by data pipeline upstream |
| Feature set versioned | src/features/ modules |
| All runs tracked in MLflow | Enforced by train entrypoint |
| Promotion gate documented | Yes — 3% SMAPE degradation threshold |
| Model card maintained | This document |
| Drift monitoring planned | Phase 2 |
