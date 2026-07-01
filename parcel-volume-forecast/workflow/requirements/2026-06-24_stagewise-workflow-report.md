# Requirements: Stage-wise Workflow Report

## 1. Business Question
How do we define a comprehensive stage-wise workflow report that documents the entire ML lifecycle from business understanding through retraining, with explicit input, derivation method, and output for each of the 15 workflow stages?

## 2. Success Criteria
1. A repeatable, stage-wise report template is defined for all 15 stages.
2. Each stage clearly documents: input, how output is derived (method), and output.
3. Reviewers can understand data cleansing, feature selection, training results, and operational outcomes at each handoff.
4. The report is linked into project docs and used during phase reviews and governance gates.

## 3. Scope
### In Scope
- Define a stage-wise report template covering all 15 stages (Business Understanding through Retraining Pipeline).
- Define three mandatory fields per stage: Input, Derivation Method, Output.
- Define data sources and evidence locations for each stage.
- Define where the report will be published and update cadence.

### Out of Scope
- Automatic generation of the report from Databricks runs (manual assembly is acceptable for Phase 1).
- Full UI/dashboard implementation.
- Changing the underlying MLflow or Databricks job definitions beyond metadata capture.

## 4. Implementation Tasks
### 4.1 Finalize template and evidence mapping
- Confirm the 15 stages and the three mandatory fields for each stage.
- Define the source artifact or data source for each criterion.
- Create the report template document at `docs/project/phase1_stagewise_report.md`.

### 4.2 Assess run readiness
- Review the latest completed Phase 1 run for stage evidence coverage.
- Determine whether the last run is sufficient or whether a new run is required.
- Document any missing stage evidence and required run artifacts.

### 4.3 Capture missing evidence and implement gaps
- Data collection: document source tables, extract queries, and raw dataset details.
- Data quality: add profiling, data-quality findings, and cleansing rules.
- Data preprocessing: confirm logic in `src/data/` and capture row-level transformations.
- Feature engineering: confirm feature definitions in `src/features/`.
- Feature selection: document feature choice rationale and selected set.
- Train/validation/test split: capture split rules, date ranges, and row counts.
- Hyperparameter tuning: capture tuning method, best params, and experiment results.
- Model training: ensure MLflow logs model artifact, params, and feature importance.
- Model evaluation: capture holdout metrics, baseline comparison, and gate decision.
- Explainability: capture explainability output, plots, or model-card notes.
- MLflow registration: record registered model version and run id.
- Batch forecast generation: capture batch scoring output location and schema contract.
- Monitoring & drift detection: capture monitoring method, alerts, and thresholds.
- Retraining pipeline: document retraining trigger conditions and workflow repeat path.

### 4.4 Produce the stage-wise report instance
- Populate the template with actual run evidence for all 15 stages.
- Reference supporting artifacts and document the derivation method for each output.
- Validate that every stage has input, derivation method, and output.

### 4.5 Publish and review
- Link the completed report from `docs/project/runbook.md` and `docs/project/decision_log.md`.
- Conduct team review with the Senior ML Engineer, DS owner, and delivery lead.
- Obtain formal approval before treating the requirement as implemented.

## 5. Stage-wise Report Structure (15 Stages)

### Stage 1: Business Understanding
**Input:** Business problem statement, success metric, decision context
**Derivation Method:** Stakeholder interview, problem framing workshop
**Output:** Defined objective, success metric (e.g., SMAPE target), prediction grain, and documented use case

### Stage 2: Data Collection
**Input:** Source table names, data warehouse schema
**Derivation Method:** Query existing tables or extract from source systems
**Output:** Raw training dataset (CSV or table reference), row count, date range, column list

### Stage 3: Data Quality Validation
**Input:** Raw training dataset from Stage 2
**Derivation Method:** Profile data for nulls, duplicates, outliers; document quality issues
**Output:** Data quality report (row counts, null percentages, anomalies), identified cleansing rules

### Stage 4: Data Preprocessing
**Input:** Quality findings and cleansing rules from Stage 3
**Derivation Method:** Apply filters, handle nulls, remove duplicates, normalize ranges
**Output:** Cleansed dataset, preprocessing logic (stored in `src/data/`), record of rows removed

### Stage 5: Feature Engineering
**Input:** Cleansed dataset from Stage 4
**Derivation Method:** Create calendar features, domain transforms, baseline aggregations
**Output:** Feature set with engineered columns, feature definitions (stored in `src/features/`)

### Stage 6: Feature Selection
**Input:** Feature set from Stage 5, business domain knowledge
**Derivation Method:** Correlation analysis, feature importance ranking, domain reasoning
**Output:** Candidate feature list, justification for inclusion/exclusion, selected feature count

### Stage 7: Train/Validation/Test Split
**Input:** Feature set from Stage 6
**Derivation Method:** Time-ordered split (train on earlier dates, test on recent), stratify if needed
**Output:** Train, validation, and test datasets with date ranges and row counts

### Stage 8: Hyperparameter Tuning
**Input:** Train/validation splits from Stage 7, candidate model type
**Derivation Method:** Grid search, random search, or Bayesian optimization
**Output:** Best hyperparameter set, tuning experiment log, performance curve

### Stage 9: Model Training
**Input:** Train dataset and best hyperparameters from Stage 8
**Derivation Method:** Fit model on training data, log hyperparams and version
**Output:** Trained model artifact, training time, feature importance, logged to MLflow

### Stage 10: Model Evaluation
**Input:** Trained model from Stage 9, validation and test datasets from Stage 7
**Derivation Method:** Calculate metrics (SMAPE, RMSE, MAE) on hold-out sets, compare to baseline
**Output:** Evaluation metrics, baseline delta, pass/fail on non-regression gate, performance report

### Stage 11: Explainability
**Input:** Trained model from Stage 9, feature importance results
**Derivation Method:** SHAP analysis, feature importance plots, prediction decomposition
**Output:** Explainability artifacts (model card section), documented model behavior and limitations

### Stage 12: MLflow Registration
**Input:** Model artifact, metrics, explainability docs
**Derivation Method:** Log model and all supporting artifacts to MLflow registry
**Output:** Registered model version in MLflow/UC, run id, CMMI process metrics

### Stage 13: Batch Forecast Generation
**Input:** Registered model from Stage 12, new data for scoring
**Derivation Method:** Apply model to batch data through workflow job
**Output:** Forecast table/view in Databricks, schema validated, served to downstream consumers

### Stage 14: Monitoring & Drift Detection
**Input:** Batch forecasts from Stage 13, production data
**Derivation Method:** Compare actual vs predicted, track metric drift over time
**Output:** Drift alerts (if any), monitoring dashboard link, anomaly report

### Stage 15: Retraining Pipeline
**Input:** Drift alerts, performance degradation, or scheduled cadence
**Derivation Method:** Trigger workflow to repeat Stages 2–12 with new data
**Output:** New model version registered, promotion decision, updated serving views

## 5. Data Sources and Evidence per Stage
- Stage 1: Requirement document, use-case memo
- Stage 2: Data dictionary, SQL query, table lineage
- Stage 3: Data quality report, profiling output
- Stage 4: `src/data/load_training_data.py` and preprocessing logic
- Stage 5: `src/features/time_features.py`, `src/features/target_transform.py`
- Stage 6: Feature correlation heatmap, domain reasoning memo
- Stage 7: Train/val/test split log, sample counts
- Stage 8: Hyperparameter tuning grid, best params JSON
- Stage 9: MLflow run artifact, model file, hyperparams logged
- Stage 10: MLflow metrics, evaluation report, baseline comparison
- Stage 11: SHAP plots, model card, limitations section
- Stage 12: MLflow run id, registered model version
- Stage 13: Forecast output table, row count, schema validation
- Stage 14: Drift report, monitoring dashboard, alert log
- Stage 15: Workflow trigger log, retraining run id

## 6. Expected Output Artifacts
1. A stage-wise report template saved at `docs/project/phase1_stagewise_report.md` with all 15 stages.
2. One example report created from a Phase 1 training run.
3. Report links added to `docs/project/runbook.md` and `docs/project/decision_log.md`.
4. A handoff checklist confirming each stage is complete before proceeding.

## 7. CMMI Gate 0
- Change type: Workflow reporting and lifecycle governance.
- Primary metric: Template completeness (all 15 stages, 3 criteria each).
- Human review: Required before implementation.

## 8. Recommended Ownership
- Owner: Senior ML Engineer persona
- Review: Project DS owner and delivery lead
- Sign-off: Product/Planning and governance sponsor

## 9. Approval Exit Gate
Requirement is complete when:
1. Template with all 15 stages and three criteria is approved by the team.
2. One stage-wise report example exists for a real Phase 1 training run.
3. The report is referenced by runbook and decision log.
4. Leadership confirms the stage definitions are clear and actionable for reviews.

## 10. Approval Request
Please confirm whether this 15-stage workflow report requirement is approved for implementation.
