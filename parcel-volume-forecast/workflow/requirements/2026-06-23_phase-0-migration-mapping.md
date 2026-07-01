# Requirements: Phase 0 Migration Mapping

## 1. Business Question
How do we move from notebook-first delivery to a structured project layout with minimal disruption and shared understanding across the team?

## 2. Success Criteria
1. The team can explain each target folder in one sentence.
2. Existing notebook steps are mapped to destination folders.
3. Migration sequence and ownership are agreed.
4. No production logic changes are made in this phase.

## 3. Scope
### In Scope
- Current-state review of notebook workflow.
- Folder purpose summary for migration.
- Notebook-step-to-folder mapping.
- Migration sequence and ownership proposal.
- Approval checkpoint before implementation.

### Out of Scope
- Refactoring production code.
- Model retraining, retuning, or architecture changes.
- Deployment changes.
- New data source onboarding.

## 4. Data Sources
- Existing notebook flow and associated project artifacts already in this workspace.
- Existing SQL and workflow assets used by the current process.
- Primary migration source notebook: Multi Client Forecast IB Uplift Analysis (Databricks workspace notebook).

## 5. Expected Output
A simple migration guide that includes:
1. Folder purpose summary.
2. Notebook-step-to-folder mapping for Multi Client Forecast IB Uplift Analysis.
3. Proposed migration sequence.
4. Owner suggestions per migration slice.
5. Approval sign-off section.

## 6. CMMI Gate 0
- Model / change type: Process and structure migration planning.
- Primary metric: Mapping completeness and stakeholder approval.
- Ethical boundary: Advisory-only planning; no automated punitive decisions.
- Human review required: Yes.

## 7. Current Phase Status
- Delivery phase: Phase 0 (migration mapping and alignment).
- Why this change belongs in this phase: It creates shared scope, ownership, and sequencing before any production logic changes.

## 8. Proposed Folder Mapping
- Notebook exploration source: `notebooks/`
- Data loading and prep logic: `src/data/`
- Feature logic: `src/features/`
- Training logic: `src/training/`
- Evaluation logic: `src/evaluation/`
- Governance/process metrics: `src/governance/`
- Workflow orchestration: `jobs/`
- Governed serving and KPI SQL: `sql/`
- Regression and unit checks: `tests/`
- Operational records and decisions: `docs/project/`
- Governance evidence and audit artifacts: `docs/ai-governance/`

## 9. Approval Request
Please confirm whether this Phase 0 requirements document is approved.

Implementation and code migration must not start until explicit approval is given.

## 10. MCP Validation Status (Databricks)
- Validation date: 2026-06-23
- Validation method: Databricks MCP live API checks
- Endpoints attempted:
	- `jobs/list`
	- `clusters/list`
	- `repos/list`
- Result: Blocked by authentication (`403 Forbidden`, `Invalid Token`)

Current-state inventory for jobs, clusters, repos, notebooks, and SQL objects is not yet verified from Databricks.
Approval can proceed for Phase 0 planning, but environment-backed state confirmation requires a valid Databricks token and a re-run of MCP validation.
