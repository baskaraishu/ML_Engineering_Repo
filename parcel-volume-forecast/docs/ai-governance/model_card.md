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
| Source table | fcast_multi_client_data_build_champion_modelv35 (analytics_sandbox) |
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
| event_black_friday, event_christmas_day, event_easter_sunday, event_uk_bank_holiday, event_eng_bank_holiday, event_peak, event_pay_week, event_prime_day, event_cyber_monday, event_boxing_day, event_halloween, event_mother_s_day, event_father_s_day, event_valentine_s_day, event_new_year_s_day, event_winter_clearance, event_sct_bank_holiday, event_nir_bank_holiday, event_wls_bank_holiday, event_st__patrick_s_day, event_chinese_holiday, event_pay_week_minus_1, event_pay_week_plus_1, event_pay_week_plus_2 | Binary event flags from live table — 1 on the event date, 0 otherwise |
| event_*_week_before / event_*_week_after | Lead/lag variants of each event flag (pre-event and post-event window) |

Total: **72 features** (60 event columns + 10 cyclical + 2 business flags). Auto-detected at runtime from the live table by `infer_feature_columns()`.

## 6. Target Variable

log(actual_volume / rolling_4w_median)

Inverse transform applied during inference to return predicted absolute volume.

---

## 7. Evaluation

| Metric | Scope | Phase-1 target |
|---|---|---|
| SMAPE (target space) | All clients | Diagnostic only; tracked per run in MLflow |
| SMAPE (business volume space) | All clients | Primary quality gate metric (`test_smape_volume`) |
| SMAPE (business volume space) | Archetype cohort | Cohort-specific threshold by operational archetype |
| Accuracy tier | Top-100 clients | Excellent / Good / Moderate / Poor |
| Promotion gate | Business-space quality and process controls | `test_smape_volume <= 40.0` AND all CMMI gates pass |

### Phase-1 first production run (2026-07-06, MLflow run `350648c6bdb04f0fb94e0414741a4475`)

| Metric | Value |
|---|---|
| Naive baseline SMAPE (test) | 33.72% |
| Model SMAPE — test (volume space) | **33.58%** |
| Model SMAPE — val (volume space) | 33.26% |
| Anchors daily-agg SMAPE | 5.27% (gate 7.5%) — ZONE_1_NOMINAL |
| Dials daily-agg SMAPE | 7.89% (gate 13.0%) — ZONE_1_NOMINAL |
| Spikers daily-agg SMAPE | 14.24% (gate 24.0%) — ZONE_1_NOMINAL |
| Phantoms daily-agg SMAPE | 23.09% (gate 32.0%) — ZONE_1_NOMINAL |
| CMMI baseline speed | 0.008 h (gate ≤ 2 h) — Pass |
| CMMI evaluation speed | 0.022 h (gate ≤ 24 h) — Pass |
| CMMI artifact completeness | 1.0 — Pass |
| `promotion_recommendation` | **True** |
| Feature count | 72 |
| Training rows | 1,011,634 |

### Operational archetype gate policy (Stage 3)

| Archetype | Threshold (Business SMAPE) | Gate impact |
|---|---:|---|
| The Anchors | 7.5 | Hard fail (critical rejection) |
| The Dials | 13.0 | Hard fail (critical rejection) |
| The Spikers | 24.0 | Warning only (deviation warning) |
| The Phantoms | 32.0 | Hard fail (critical rejection) |

The training report now logs per-cohort evidence under `operational_archetype_briefing` with a workflow impact flag:
- `ZONE_1_NOMINAL`
- `ZONE_2_DEVIATION_WARNING`
- `ZONE_3_CRITICAL_REJECTION`

Promotion context is logged under `promotion_context` with:
- `promotion_gate_metric`
- `promotion_gate_threshold`
- `promotion_gate_value`
- `promotion_block_reason`

---

## 8. Known Limitations and Risks

- Calendar features cover named UK/international events but do not capture unscheduled disruptions (strikes, operational incidents)
- Client-level accuracy varies significantly across low/high-volume segments, which is mitigated operationally using archetype-specific thresholds
- Uplift target assumes 4-week median is a stable baseline — volatile clients may drift
- Model has no built-in uncertainty quantification
- Global SMAPE (~33%) reflects the irreducible noise floor in sparse Phantom clients; per-archetype SMAPE for stable Anchor clients is ~5%

---

## 9. CMMI L5 Governance Controls Applied

| Control | Status |
|---|---|
| Problem framing and success criteria defined | Yes |
| Dataset version recorded | Required per run |
| PII controls | Enforced by data pipeline upstream |
| Feature set versioned | src/features/ modules |
| All runs tracked in MLflow | Enforced by train entrypoint |
| Promotion gate documented | Yes — business-space gate + archetype cohort policy |
| Model card maintained | This document |
| Drift monitoring planned | Phase 2 |
