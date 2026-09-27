# Project - Decision Log

Record key decisions here so future engineers can understand the reasoning.

---

## 2026-06-21 — Adopt folder-structured scaffold from Genie notebook

Decision: Move from notebook-only delivery to src/jobs/sql/tests/docs scaffold.
Rationale: Notebook-only workflow lacks reproducibility and promotion gates for production use.
Alternative considered: Continue in notebook with structured cells only.
Why rejected: No reliable test coverage, CI enforcement, or CMMI evidence trail.

---

## 2026-06-21 — Use XGBoost as Phase 1 model

Decision: Promote XGBRegressor from existing Genie notebook as Phase 1 training entrypoint.
Rationale: Already validated by team, has MLflow logging, and is registered in Unity Catalog.
Alternative considered: Start from scratch with Prophet or LightGBM.
Why rejected: No evidence of improvement; fast adoption is the priority in Phase 1.

---

## 2026-06-21 — Low-volume client filter threshold = median daily > 10

Decision: Exclude clients with median daily volume ≤ 10.
Rationale: Matches current notebook logic; very small clients introduce noise without planning value.
Review: Reassess threshold at Phase 2 with business stakeholders.

---

## 2026-06-23 — Segregate AI governance docs from project docs

Decision: Split docs/ into ai-governance/ (model card, bias, lineage) and project/ (runbook, decisions).
Rationale: AI governance artifacts need to be independently auditable and versioned separately from ops notes.

---

## 2026-06-23 — Temporarily host prompt files at workspace root

Decision: Move prompt files from `parcel-volume-forecast/.github/prompts/` to `ML Workspace/.github/prompts/`.
Rationale: Active VS Code workspace root is `ML Workspace`, and prompt discovery is workspace-root scoped in current usage.
Alternative considered: Keep prompts repository-local and change workspace root immediately.
Why rejected: Team needed immediate prompt discoverability without interrupting active parent-workspace session.
Exit condition: Move prompts back to `parcel-volume-forecast/.github/prompts/` when `parcel-volume-forecast` is opened as its own workspace root.

---

## 2026-06-23 — Phase 1 quick-win execution checkpoint (local)

Decision: Accept local Phase 1 checkpoint evidence and continue implementation toward full exit-gate closure.
Rationale: Local training run and tests completed; CMMI process metrics and gate flags were captured for the run.
Evidence:
- Local MLflow run id: `f9c245ca18e04fcf8d9c2a7977474ea5`
- `test_smape_target`: `12.721666882742863`
- `cmmi_baseline_speed_pass`: `True`
- `cmmi_evaluation_speed_pass`: `True`
- `cmmi_artifact_completeness_pass`: `True`
Open item: Performance non-regression gate remains pending until baseline/champion reference value is confirmed for comparison.

---

## 2026-06-24 — Add structure clarity and workflow reporting requirement

Decision: Add a CMMI L5 repository structure guide and create a separate requirement for Databricks-style workflow reporting.
Rationale: Team feedback indicated uncertainty around folder/file purpose and missing standardized leadership workflow reporting expectations.
Expected outcome: Faster onboarding clarity, consistent report format, and stronger CMMI evidence traceability.
