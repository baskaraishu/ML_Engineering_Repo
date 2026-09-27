# AI Governance - Bias and Risk Assessment
# Model: XGBoost Multi-Client Forecast IB Uplift Analysis
# Phase: 1 (MVP)

---

## 1. Risk Classification

| Risk area | Level | Rationale |
|---|---|---|
| Automated harm | Low | Advisory only — human planners review outputs |
| Data privacy | Low | No customer PII in training features |
| Fairness (client-level) | Medium | Low-volume clients excluded; accuracy varies by segment |
| Operational failure | Medium | Stale or missing features could silently degrade accuracy |
| Explainability | Low | SHAP analysis available per run |

---

## 2. Identified Biases

| Bias type | Description | Mitigation |
|---|---|---|
| Volume segment bias | Low-volume clients filtered; model not validated on this group | Document and communicate to stakeholders |
| Seasonal distribution | Training window may underrepresent unusual peak events | Review training window coverage each quarter |
| Client composition drift | Champion v35 client list may exclude new or exited clients | Refresh client filter quarterly |

---

## 3. Guardrails in Place

- Minimum volume filter enforced in src/data/load_training_data.py
- Holdout test set never seen during training or tuning
- SMAPE promotion gate prevents regression vs champion
- Human review required before forecast published to planning app

---

## 4. Residual Risks

- Drift detection not implemented in Phase 1 (deferred to Phase 2)
- No automated alert when prediction distribution shifts significantly
- No confidence/uncertainty intervals provided to end users

---

## 5. Review Cadence

- Model card and risk assessment reviewed each model version update
- Stakeholder sign-off required before production promotion
