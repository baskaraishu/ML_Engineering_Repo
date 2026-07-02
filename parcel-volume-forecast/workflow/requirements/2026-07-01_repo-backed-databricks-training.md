# Requirements: Repo-Backed Databricks Training Operating Model

## 1. Business Question
How do we standardize the production training path so that code is authored and versioned in Git, executed by Databricks Jobs from the repository training entrypoint, and tracked in MLflow Experiments with consistent governance artifacts?

## 2. Success Criteria
1. Production training is defined as a repo-backed execution path using `src/training/train_xgboost.py`.
2. Databricks Jobs are configured to trigger the production training path from repository-controlled code, not notebook-only business logic.
3. MLflow Experiments capture the run metrics, params, model artifacts, and repo-generated governance report artifacts for each production run.
4. Local smoke runs are explicitly defined as preflight validation only and are separated from production-tracked Databricks runs.
5. Production triggering is standardized through CLI-driven CI/CD rather than notebook-backed or manual UI-only execution.
6. The operating model is documented clearly enough that a junior engineer can distinguish source-of-truth code, execution environment, tracking sink, and verification steps.
7. Runtime data source parameters (for example `source_table`) are resolved at the entrypoint/orchestration layer, with production requiring explicit Job/CI values and local preflight allowed to use controlled defaults.

## 3. Scope
### In Scope
- Define the target-state production execution path as Git -> Databricks Job -> repo training entrypoint -> MLflow Experiment.
- Define how local smoke runs relate to Databricks production runs.
- Define the expected Databricks job shape for production training.
- Define MLflow expectations for local versus Databricks tracking.
- Define governance/report artifact expectations for production runs.

### Out of Scope
- Building a full Databricks Asset Bundle deployment framework in this phase.
- Converting all exploratory notebooks into source modules immediately.
- Designing model registry promotion workflows beyond the current training/reporting scope.

## 4. Target Operating Decision
### 4.1 Production training source of truth
- Production training code must live in repository-controlled files under `src/`.
- The canonical production training entrypoint is `src/training/train_xgboost.py`.
- Notebook-only training logic is not an acceptable long-term production source of truth.

### 4.2 Notebook role
- Notebooks remain valid for exploration, diagnostics, and rapid iteration.
- Notebooks are not part of the approved long-term production training path.
- If a notebook is retained in the production path temporarily during transition, it must act only as a thin wrapper that delegates to repository-backed logic.
- Business-critical logic must not diverge between notebook and repository implementations.

### 4.3 Databricks job role
- Databricks Jobs are the operational trigger mechanism for production training.
- The production Databricks Job must call the repository-backed training entrypoint.
- CLI and CI/CD triggering are the approved operational trigger mechanism for production training.
- Manual UI-only execution is allowed for diagnostics but is not the standard production operating path.

### 4.4 MLflow role
- MLflow Experiments are the canonical tracking sink for Databricks production runs.
- Repo-backed runs must still log to MLflow Experiments exactly as notebook-backed runs do.
- The repository-generated report artifacts must be visible as MLflow artifacts for each governed production run.

## 5. Required Execution Model
### 5.1 Production path
1. Engineer pushes code to Git.
2. CI/CD syncs or deploys the repository code into the Databricks execution environment.
3. CI/CD triggers the Databricks Job.
4. Databricks Job runs `src/training/train_xgboost.py` from the deployed repository-backed path.
5. Training reads the Databricks runtime input source (currently DBFS CSV path unless changed).
6. Training logs metrics, params, model artifacts, and governance report artifacts to MLflow.
7. Reviewers validate the run using Databricks run state plus MLflow evidence.

#### 5.1 Status
- Done:
  - The repository-backed training entrypoint is defined in `src/training/train_xgboost.py`.
  - The Databricks job contract points to the repo-backed entrypoint and passes the expected runtime parameters.
  - The runtime input source is wired to the DBFS CSV path in the job contract.
  - MLflow logging and governance report emission are implemented in the training entrypoint.
  - The live Git-backed Databricks job is able to reach the repository code path.
  - The Databricks task now explicitly provisions `xgboost==3.3.0` so the runtime dependency is declared in the job contract.
- Done (post-debug):
  - Declared `xgboost==3.3.0` in the serverless environment spec (`environments[].spec.dependencies`) — not the task-level `libraries` block which only applies to classic clusters.
  - Uploaded the training CSV to `/Workspace/Shared/forecasting/multi_client_ib_uplift.csv`. Serverless Jobs Compute v2 does not mount `/dbfs/`; Workspace paths are required.
  - Updated the job's `--input-csv` parameter to the Workspace path and re-applied the reset.
  - Confirmed run `123480460228569` completed with `result_state: SUCCESS`.
  - MLflow Experiment `/Shared/forecasting/parcel-volume-forecast` was created and logged: 12 features, model artifact, CMMI gates, `run_summary.json`, `run_summary.html`.
- Pending:
  - Propagate the `/Workspace/Shared/forecasting/` input path convention into the runbook and other reset payloads.
  - CI/CD-triggered deployment and trigger automation are not yet proven end-to-end.

### 5.2 Local smoke path
1. Engineer runs local smoke from repository root.
2. Smoke run validates packaging, imports, feature flow, training flow, and report emission locally.
3. Local smoke run must not be treated as proof that the Databricks production run succeeded.
4. Local smoke tracking should remain separated from Databricks production tracking using file-backed MLflow or a separate experiment namespace.

### 5.3 Runtime parameterization path (source table)
1. Data-loading modules keep explicit function arguments for runtime sources (for example `source_table`) and do not hardcode environment-specific table names.
2. The training entrypoint/orchestration layer resolves runtime values using precedence: CLI argument -> environment variable -> local config default.
3. Production Databricks Jobs and CI/CD must pass `source_table` explicitly; production must not rely on local defaults.
4. Environment allowlists must be enforced so production rejects unapproved table names.

### 5.4 Phase 0 compute fallback path
1. If job-triggered runs fail with compute permission errors, the Databricks Job may temporarily use an existing notebook-accessible cluster to unblock validation.
2. This fallback is transitional and must be replaced by a shared, schedule-compatible job compute target.
3. Runs executed through this fallback still require repo-backed entrypoint usage and MLflow evidence logging.

### 5.5 Phase 0 notebook-launcher POC path
1. A notebook may be used as a launcher only, where cells invoke repository code under `src/` (for example `src/training/train_xgboost.py`) rather than embedding notebook-only business logic.
2. This path is allowed as a pre-admin POC to validate repo-backed execution and MLflow evidence when job-compute permissions are blocked.
3. POC runs must use debug mode markers (for example `run_mode=debug`) and must not be treated as production promotion evidence.
4. The notebook-launcher path does not replace the Databricks scheduled job path and does not satisfy production orchestration acceptance criteria.

## 6. Current Risks to Eliminate
1. Notebook-only drift: production behavior differs from reviewed repository code.
2. Ambiguous MLflow interpretation: run appears in Experiment but did not pass through the governed repo entrypoint.
3. Duplicate verification runs: engineers trigger local smoke after Databricks training and mistake that for remote-run validation.
4. Unclear deployment path: Databricks job points to unstable or placeholder workspace paths instead of controlled repository-backed paths.
5. Audit gaps: training succeeds operationally but does not generate repo-defined governance artifacts.
6. Manual runtime variance: production jobs are triggered from the UI instead of a controlled CI/CD path.

## 7. Required Technical Controls
### 7.1 Repository-backed entrypoint control
- `src/training/train_xgboost.py` remains the canonical production entrypoint.
- Databricks job parameters must match the argument contract of that file.

### 7.2 Job configuration control
- The job definition in `jobs/train_job.yaml` is the repository contract for production execution.
- Any live Databricks job must be kept aligned to that contract or to an explicitly approved deployed derivative.
- Production jobs must not depend on notebook-backed business logic as their primary execution path.
- Production jobs must pass approved runtime table parameters explicitly (for example `source_table`) rather than inheriting local defaults.
- Phase 0 may temporarily bind the job to an existing notebook-accessible cluster to bypass permission blockers, but this does not change the repo-backed execution requirement.

### 7.3 Runtime parameter control
- Loader functions accept runtime inputs explicitly (for example `source_table`) to preserve reusability and testability.
- Defaults for local convenience may exist in central config, but only for local/preflight workflows.
- Production execution must fail fast when required runtime parameters are missing.
- Production execution must fail fast when runtime table values are outside the environment allowlist.

### 7.4 MLflow control
- Production runs must log to the Databricks MLflow Experiment namespace.
- Local smoke runs must use a separate local/file-backed tracking target or clearly separate experiment name.
- CLI-triggered debug runs are allowed as a controlled exception but must use a debug marker (for example `run_mode=debug`) and must not be used as promotion evidence.

### 7.5 Reporting control
- Production runs must emit:
  - model metrics
  - CMMI process metrics
  - `run_summary.json`
  - `run_summary.html`
- These artifacts are part of the governed production evidence pack.

## 8. Implementation Tasks
### 8.0 Phase 0 quick win (minimum viable migration)
- Replace any remaining hardcoded runtime table references with a central config value.
- Keep loader interfaces explicit (for example `source_table` argument) and resolve defaults in the entrypoint/orchestration layer.
- Preserve current behavior for local/preflight runs by using the config-backed default.
- Do not block this phase on full production allowlist enforcement or CI policy gates.
- If compute permissions block job runs, execute a notebook-launcher POC that calls repository modules and logs debug-marked MLflow evidence.

### 8.1 Clarify and document the operating model
- Update runbook wording so local smoke is documented as preflight validation only.
- Update architecture/onboarding docs to define production as repo-backed execution.
- Update docs to make Databricks schedule setup inside Databricks the Phase 0 trigger path.

### 8.2 Align Databricks job definition
- Ensure the Databricks job points to the repository-backed training entrypoint.
- Ensure deployment uses a valid Databricks-resolvable repository path.
- Ensure runtime parameters match the production contract.
- Remove notebook-backed production execution as the primary job mode.
- If needed to unblock, bind the job to a permitted existing cluster in Phase 0 and track this as a temporary exception until shared job compute is provisioned.

### 8.3 Standardize Databricks schedule triggering
- Define the Databricks Job schedule inside Databricks for the production training workflow.
- Ensure the Databricks schedule is the primary Phase 0 trigger mechanism.
- Ensure manual UI or CLI triggering remains possible for controlled diagnostics.
- Ensure CLI-to-Experiment debug runs are explicitly documented as non-production evidence.

### 8.4 Standardize runtime parameter handling
- Add and document local-only config defaults for runtime data sources where needed.
- Add entrypoint logic for runtime parameter precedence (CLI -> env -> local config default).
- Add production guardrails that require explicit `source_table` from Job/CI input.
- Add production allowlist validation for approved table names by environment.

### 8.5 Separate local and production tracking
- Confirm local smoke instructions use file-backed MLflow or a separate experiment namespace.
- Confirm Databricks production runs log into the intended shared Experiment path.

### 8.6 Strengthen verification flow
- Define the post-run verification checklist for Databricks runs:
  - Job/task state
  - MLflow metrics
  - model artifact
  - governance report artifacts

## 9. Expected Output Artifacts
1. A documented operating requirement for Git -> Databricks Job -> repo entrypoint -> MLflow.
2. A Databricks job contract aligned to the repository training entrypoint.
3. Runbook guidance that separates local smoke verification from Databricks production verification.
4. A reproducible Databricks-scheduled production training path for Phase 0.
5. A documented debug exception path for CLI-triggered troubleshooting runs that are excluded from promotion evidence.

## 10. Decision Statement
The approved target state is:
- Production training is repo-backed.
- Databricks Jobs provide orchestration.
- MLflow Experiments provide tracking and artifact lineage.
- Notebooks are exploratory or thin-wrapper interfaces, not the long-term production logic source.
- Notebook-backed production runs are removed as the standard operating model.
- Databricks-scheduled execution is the preferred Phase 0 trigger path.

## 11. Approval Exit Gate
This requirement is complete when:
1. The team agrees that production training source of truth is the repository entrypoint.
2. The runbook and supporting docs reflect the approved operating model.
3. The Databricks job can be triggered from CLI against the repo-backed path.
4. CI/CD can trigger the Databricks production job using the approved path.
5. A Databricks production run produces MLflow metrics and repo-defined governance report artifacts.

## 12. Approval Request
Please confirm this operating model requirement for implementation and adoption.