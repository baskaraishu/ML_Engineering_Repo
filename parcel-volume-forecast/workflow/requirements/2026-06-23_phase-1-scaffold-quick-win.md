# Requirements: Phase 1 Scaffold Quick Win

## 1. Business Question
How do we deliver a fast, low-risk Phase 1 migration from notebook-first forecasting to reproducible repository-based training and evaluation, while adopting CMMI Level 5 controls?

## 2. Success Criteria
1. The reference notebook flow (Multi Client Forecast IB Uplift Analysis) is represented in reusable modules under `src/`.
2. Local training and evaluation run deterministically from the repository using the Phase 1 scaffold.
3. Forecast quality is measured with regression-appropriate metrics and compared against baseline.
4. CMMI process metrics and gate outcomes are captured for the run.
5. Tests covering core transforms and governance calculations pass.

## 3. Scope
### In Scope
- Migrate selected reusable logic from notebook flow into `src/data/`, `src/features/`, `src/training/`, and `src/evaluation/`.
- Execute local training + evaluation for Phase 1 quick-win validation.
- Capture CMMI process metrics and gate evidence.
- Update required project/governance records for traceability.

### Out of Scope
- Production deployment or endpoint rollout.
- Major architecture/model replacement beyond Phase 1 parity objective.
- Full drift and online monitoring hardening (Phase 2).
- New source-system onboarding.

## 4. Data Sources
- Primary migration source notebook: Multi Client Forecast IB Uplift Analysis.
- Existing training extract and local/project artifacts already referenced by the current scaffold.
- Existing SQL and workflow definitions used by current process.

## 5. Expected Output
1. Reusable Phase 1 migration logic in `src/` with deterministic local run instructions.
2. One reproducible training run record with evaluation outputs.
3. Baseline versus current quick-win comparison summary.
4. Updated tests for migrated logic and governance metrics.
5. Updated docs under `docs/project/` and, where applicable, `docs/ai-governance/`.
6. Leadership-facing Phase 1 summary artifact with model performance, CMMI gate status, risks, and go/no-go recommendation.

## 6. CMMI Gate 0
- Model / change type: Phase 1 migration and process hardening (quick win).
- Primary metric: `test_smape_target` (with non-regression control versus baseline).
- Ethical boundary: Advisory-only forecasting; no automated punitive decisions.
- Human review required: Yes.

## 7. Current Phase Status
- Delivery phase: Phase 1 (MVP scaffold and governance foundations).
- Why this change belongs in this phase: It operationalizes reusable training/evaluation while preserving speed and governance evidence.

## 8. Proposed Folder Mapping
- Notebook exploration source: `notebooks/`
- Data logic: `src/data/`
- Feature logic: `src/features/`
- Training logic: `src/training/`
- Evaluation logic: `src/evaluation/`
- Governance/process metrics: `src/governance/`
- Workflow orchestration assets: `jobs/`
- Governed SQL assets: `sql/`
- Regression checks: `tests/`
- Operational records: `docs/project/`
- Governance evidence: `docs/ai-governance/`

## 9. AI-Assisted Workflow Simplification Task Breakdown
Phase 1 execution should use AI support for speed, while keeping human approval at each gate.

1. Task: Extract notebook step inventory
- Input: Multi Client Forecast IB Uplift Analysis notebook flow.
- AI-assisted output: Step list grouped by data, feature, train, evaluate, and governance activities.
- SENIOR ML Engineer persona review: Confirm completeness before migration.

2. Task: Map notebook steps to repository folders
- Input: Step inventory and approved folder mapping.
- AI-assisted output: Step-to-folder mapping for `src/data/`, `src/features/`, `src/training/`, `src/evaluation/`, `src/governance/`, `tests/`, `sql/`, and `jobs/`.
- SENIOR ML Engineer persona review: Confirm ownership and migration order.

3. Task: Generate migration-ready module stubs
- Input: Approved step-to-folder mapping.
- AI-assisted output: Small reusable module skeletons and function signatures only.
- SENIOR ML Engineer persona review: Approve interfaces before logic implementation.

4. Task: Implement migrated logic in slices
- Input: Approved interfaces and notebook reference behavior.
- AI-assisted output: Incremental code changes per slice (data, features, training, evaluation).
- SENIOR ML Engineer persona review: Validate scope remains within approved requirement.

5. Task: Add and run quality checks
- Input: Migrated slices and governance metric functions.
- AI-assisted output: Updated tests and validation commands for deterministic runs.
- SENIOR ML Engineer persona review: Review failing tests and accept fixes.

6. Task: Produce gate evidence bundle
- Input: Local run outputs and metric artifacts.
- AI-assisted output: Exit-gate evidence summary including `test_smape_target`, CMMI metrics, and pass/fail flags.
- SENIOR ML Engineer persona review: Go/no-go decision recorded in project docs.

7. Task: Update governance and operational records
- Input: Final Phase 1 outputs and decisions.
- AI-assisted output: Draft updates for `docs/project/decision_log.md`, `docs/project/runbook.md`, and impacted files under `docs/ai-governance/`.
- SENIOR ML Engineer persona review: Final reviewer approval before closeout.

## 10. Expected Exit Gate (Phase 1)
Phase 1 is complete only if all criteria below are met:

1. Reproducibility Gate
- A local run of the Phase 1 pipeline completes successfully from repository code.
- Run configuration and dataset version are recorded.

2. Performance Gate
- `test_smape_target` is produced and documented.
- Non-regression rule: `test_smape_target` degradation is not greater than 3% versus the current baseline/champion reference used for Phase 1.

3. Quality Gate
- Existing and new relevant tests pass (`tests/`), including governance metric tests.
- No unresolved critical errors in the migrated path.

4. CMMI Process Gate
- Required CMMI metrics are captured for the run:
  - hours to baseline
  - hours to evaluation
  - artifact completeness
  - gate pass/fail flags
- Gate decision is documented with rationale.

5. Documentation Gate
- `docs/project/decision_log.md` updated with Phase 1 outcome.
- `docs/project/runbook.md` updated if execution steps changed.
- Governance docs updated when migration affects lineage/model evidence.
- Leadership summary artifact created and linked from project docs.

6. Approval Gate
- Human reviewer explicitly approves Phase 1 completion before any production promotion activity.

## 11. Constraints and Assumptions
- Databricks MCP live-state validation may remain blocked until token access is restored.
- Phase 1 acceptance can proceed on local evidence for scaffold completion, with environment-backed validation tracked as a follow-up control.

## 12. Approval Request
Please confirm whether this Phase 1 requirements document is approved.

Implementation must remain within this scope and exit-gate definition.

## 13. Progress Tracking (Execution Snapshot)
Last updated: 2026-06-23

Task progress for Section 9:
1. Extract notebook step inventory: Completed
2. Map notebook steps to repository folders: Completed
3. Generate migration-ready module stubs: Completed (existing scaffold modules validated)
4. Implement migrated logic in slices: In progress (current repository already contains Phase 1 slices in `src/data/`, `src/features/`, `src/training/`, `src/evaluation/`)
5. Add and run quality checks: Completed (`pytest -q` passed: 2 passed)
6. Produce gate evidence bundle: Completed (local MLflow run captured)
7. Update governance and operational records: In progress (Phase 1 checkpoint entries updated in project docs)
8. Create leadership-facing output artifact: Completed (`docs/project/phase1_leadership_summary.md`)

Evidence snapshot:
- Local run id: `f9c245ca18e04fcf8d9c2a7977474ea5`
- Dataset version: `v1-phase1-local`
- `test_smape_target`: `12.721666882742863`
- `val_smape_target`: `13.986387685793368`
- `cmmi_hours_to_baseline`: `9.265e-06`
- `cmmi_hours_to_evaluation`: `0.0065858052777777775`
- `cmmi_artifact_completeness`: `1.0`
- `cmmi_baseline_speed_pass`: `True`
- `cmmi_evaluation_speed_pass`: `True`
- `cmmi_artifact_completeness_pass`: `True`

Exit-gate status snapshot (Section 10):
1. Reproducibility Gate: Pass (local run completed from repository code)
2. Performance Gate: Partial (metric produced; non-regression comparison pending baseline reference confirmation)
3. Quality Gate: Pass (current tests passed)
4. CMMI Process Gate: Pass (metrics and gate flags captured)
5. Documentation Gate: Pass (leadership summary artifact created and linked from project docs)
6. Approval Gate: Pending SENIOR ML Engineer persona review

## 14. Leadership Output Artifact Specification
Required artifact path:
- `docs/project/phase1_leadership_summary.md`

Minimum required sections:
1. Executive Summary (Phase objective and current completion status)
2. Key Metrics (`test_smape_target`, `val_smape_target`, non-regression status)
3. CMMI Level 5 Gate Snapshot (pass/fail with rationale)
4. Risks and Open Items (including environment validation constraints)
5. Recommendation (go/no-go for next phase step)
6. Evidence Links (run id, requirements doc, decision log, runbook)