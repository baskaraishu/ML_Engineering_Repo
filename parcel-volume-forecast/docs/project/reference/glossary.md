# GLOSSARY: PARCEL-VOLUME-FORECAST QUALITY ENGINE

This glossary defines the machine learning, process governance, and MLOps terms utilized across the `parcel-volume-forecast` repository architecture, mapping them directly to traditional Software Quality Assurance (QA) and Automated Testing equivalents.

---

## 1. Core Run Context & Orchestration

### Run ID
* **ML Context:** A unique, system-generated alphanumeric identifier assigned to a single, discrete execution of an ML pipeline run within MLflow.
* **QA Parallel:** **Jenkins / GitHub Actions Build Number.** It functions as an immutable execution fingerprint, logging the exact state of code, inputs, and outputs for a specific automated test run.

### Dataset Version
* **ML Context:** A unique tag, hash, or snapshot ID capturing the exact state and lineage of data inputs (e.g., Delta Lake table versions) passed to the training pipeline.
* **QA Parallel:** **Test Fixture / Static Data Mock Version.** It locks down the exact test payload data used during the execution run, preventing environmental data changes from introducing variable results.

### Reproducibility Gate
* **ML Context:** An automated integration checkpoint validating that a pipeline execution can be completely recreated from source repository code, explicit dependencies, and designated configuration files.
* **QA Parallel:** **Environment Determinism.** It ensures that running a test script across disparate nodes (e.g., local machine vs. Databricks cluster) yields an identical output behavior every single time without local machine configuration drift.

---

## 2. Statistical Performance Metrics

### Target Variable (Target)
* **ML Context:** The dependent variable or column that the machine learning model is trained to predict (in this repository: future physical parcel volumes).
* **QA Parallel:** **The Expected Output / Test Assertion Value.** The benchmark value against which the actual runtime calculation is evaluated.

### Uplift Modeling
* **ML Context:** A modeling approach that predicts incremental change relative to a baseline, rather than absolute volume. In this repo, uplift is expressed as the log ratio of actual volume to the rolling baseline.
* **QA Parallel:** **Delta Validation.** A test that verifies change against a controlled baseline, similar to comparing output deltas against a golden master.

### Transform Contract
* **ML Context:** The agreed behavior of the feature/target transform functions, including input expectations and output semantics. This repo's transform contract defines how `actual_volume`, `rolling_4w_median`, and generated uplift targets must behave.
* **QA Parallel:** **Interface Contract Test.** A contract test verifies that inputs and outputs adhere to a stable API and that edge cases are handled predictably.

### Round-Trip Transform
* **ML Context:** The property that a forward transform and inverse transform together restore the original value, within numerical tolerance. For this repository, `build_uplift_target()` followed by `invert_uplift_target()` should reconstruct `actual_volume` from the uplift target and baseline.
* **QA Parallel:** **Serialization Round-Trip Test.** A test that verifies serialization and deserialization preserve the original data exactly or within defined tolerance.

### SMAPE (Symmetric Mean Absolute Percentage Error)
* **ML Context:** An accuracy metric measuring the percentage variance between the model's predictions and actual outcomes, mathematically bounded between 0% and 200%. 
* **QA Parallel:** **SLA Performance Tolerance.** Instead of a binary Pass/Fail assertion, SMAPE functions as an acceptable performance threshold (e.g., asserting that the prediction error is within a $\le 10\%$ operational boundary).

### test_smape_target
* **ML Context:** The calculated SMAPE percentage error achieved on an isolated testing dataset that was reserved completely outside the model fitting lifecycle.
* **QA Parallel:** **Functional Automated Test Suite Execution.** A validation execution run against a clean test data payload to evaluate structural correctness before a release decision.

### val_smape_target
* **ML Context:** The SMAPE error score achieved on a secondary, real-time validation split data slice used during iterative pipeline tuning to monitor generalization capabilities, ensuring the application didn't simply "memorize" the inputs.
* **QA Parallel:** **Sanity / Boundary Test Suite Execution.** A localized, targeted test verification loop used to verify system behavior against overfitting or logic leakage before passing code to wider environments.

* **Industry-Standard Operational Ranges:**
  * **$< 5\%$ (Exceptional / World Class):** Highly stable data distributions; ideal for immediate automated downstream logistical routing.
  * **$5\% - 15\%$ (Target Production Grade):** Industry standard for complex, variable supply-chain and time-series forecasting. **This is your target boundary for Phase 0.**
  * **$15\% - 25\%$ (Borderline / Conditional Pass):** Requires close shadow monitoring or fallback default parameters before promotion.
  * **$> 25\%$ (Failed Gate):** High risk of operational disruption (e.g., severe fleet under-ordering). Triggers an automatic deployment block.

### Non-Regression Status
* **ML Context:** A pipeline guardrail asserting that a newly trained model candidate performs statistically better than, or equal to, the baseline accuracy of the currently active production model.
* **QA Parallel:** **Performance Regression Gate.** A software check ensuring that a new code deployment does not degrade existing system SLAs or break production capabilities.

### Champion Model / Reference
* **ML Context:** The current, high-performing model deployed to production that serves active operational business requests.
* **QA Parallel:** **Production Golden Master Build.** The current stable, validated version of software serving as the definitive baseline reference for all future builds.

---

## 3. Governance & Process Metrics (CMMI Level 5)

### CMMI Level 5 (Optimizing)
* **ML Context:** The highest level of process maturity within the Capability Maturity Model Integration framework, characterized by automated, data-driven continuous process improvement and statistical control.
* **QA Parallel:** **Continuous Automated Quality Optimization.** Shifting away from manual code signing to automated pipelines that mathematically audit, measure, and record test-process execution telemetry.

### cmmi_hours_to_baseline
* **ML Context:** A process metric tracking the engineering or compute duration required to successfully establish a stable, reproducible runtime environment baseline configuration.
* **QA Parallel:** **Environment Setup Velocity.** The tracked automated cycle time needed to spin up, configure, and prepare clean test runners.

### cmmi_hours_to_evaluation
* **ML Context:** A telemetry metric tracking the elapsed processing time spent executing validation calculations, automated test passes, and final metrics aggregation.
* **QA Parallel:** **Test Execution Cycle Time.** The total runtime duration of an automated test automation script from initialization to test report compilation.

### cmmi_artifact_completeness
* **ML Context:** A governance metric calculating the structural ratio of successfully generated compliance and lineage documents relative to the mandatory enterprise pipeline requirements.
* **QA Parallel:** **Code / Requirement Coverage Analysis.** The quantifiable audit verification that all expected test results, deployment blueprints, and run evidence documents were built and archived without omissions.

---

## 4. Metrics & KPI Terms

### Metric
* **ML Context:** A numeric measure recorded during a model run, such as error rates, latency, or process durations. Metrics are used to compare candidate models and monitor production behavior.
* **QA Parallel:** **Test Result Value.** The numeric outcome reported by a test case or performance check, such as pass rate, response time, or coverage percentage.

### KPI (Key Performance Indicator)
* **ML Context:** A higher-level metric that is critical to business or governance decisions, such as `test_smape_target` or `cmmi_hours_to_evaluation`.
* **QA Parallel:** **Release Criteria Indicator.** The acceptance threshold used to decide whether a build or deployment meets quality standards.

### MLflow metric
* **ML Context:** A scalar value logged by MLflow during a run, persisted for tracking and comparison across runs.
* **QA Parallel:** **Automated Test Metric.** The recorded numeric result of a validation step, logged for review across executions.

### MLflow parameter
* **ML Context:** A configuration value recorded with a run, such as `dataset_version`, `feature_count`, or `model_name`.
* **QA Parallel:** **Test Configuration Setting.** The input or environment setting used for a specific test execution.

### MLflow artifact
* **ML Context:** A file or directory logged to MLflow, including models, reports, plots, and JSON summaries.
* **QA Parallel:** **Test Output Artifact.** The file generated by a test run, such as logs, screenshots, or coverage reports.

### Promotion rate
* **ML Context:** The fraction of candidate runs that are marked as promoted in the governance record.
* **QA Parallel:** **Deployment Acceptance Rate.** The percentage of builds that pass all quality checks and move to the next stage.

### Baseline speed
* **ML Context:** The time taken for the run to reach a stable baseline configuration or baseline-ready state.
* **QA Parallel:** **Setup Speed.** The time required to prepare the environment and test data before the main test execution begins.

### Evaluation speed
* **ML Context:** The elapsed time from start to completion of evaluation calculations and metric logging.
* **QA Parallel:** **Test Execution Duration.** The total runtime of the verification phase.

### Drift detection latency
* **ML Context:** The time between the start of a predicted distribution shift event and when drift is detected by monitoring.
* **QA Parallel:** **Regression Detection Delay.** The lag between the introduction of a defect and the moment it is observed by automated tests.

### Process KPI
* **ML Context:** A metric that measures the health of the ML development process, not just model accuracy.
* **QA Parallel:** **CI/CD Pipeline Metric.** A measurement of process efficiency, such as build duration, environment readiness, or test completeness.

