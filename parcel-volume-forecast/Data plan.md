# Data Plan

## Objective

Establish a reusable Databricks data refinery plan for the parcel volume forecasting workload, based on live discovery of the production Unity Catalog environment.

## Discovery Findings

### Candidate tables discovered

- `evri_datalakehouse_prod_catalog.cent_analytics_gold.fcast_actuals`
- `evri_datalakehouse_prod_catalog.cent_analytics_gold.fcast_predictions`
- `evri_datalakehouse_prod_catalog.cent_analytics_gold.fcast_predictions_adjusted`
- `evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35`
- `evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multiclient_preadvice_network_forecasts`
- `evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_preadvice_medians`
- `evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_ib_uplift`

### Champion asset verdict

The strongest evidence-based champion feature asset is:

`evri_datalakehouse_prod_catalog.analytics_sandbox.fcast_multi_client_data_build_champion_modelv35`

Reasons:

- It was updated on 2026-07-05, while `fcast_multi_client_data_build_champion_ib_uplift` was last updated on 2026-02-10.
- It matches the active daily retrain lineage in `analytics_sandbox`.
- The older `champion_ib_uplift` table appears to be a frozen snapshot, not the current production-grade build.

## Raw Structural Footprint

### Confirmed semantic role of columns

- `preadvice_date` is the source date column.
- `parcel_volume` is the observed volume.
- `median_4wk_volume` is the baseline feature.
- `target` exists as a precomputed field in the live table and should be preferred over recomputation where provenance is trusted.
- `china_flag` and `domestic_flag` are binary business flags.
- `client_name` is present and must be reviewed for PII classification before any production training decision.

### Natural filter boundaries

The live table contains a large volume of unusable rows that are not model-ready:

- Rows outside the lookback window should be excluded in Spark before collection.
- Rows with null `preadvice_date`, null `parcel_volume`, or null `median_4wk_volume` should be excluded.
- Rows with `median_4wk_volume <= 0` should be excluded because uplift is undefined for zero-history clients.

## 3-Stage Data Refinery Framework

### Stage 1: Verification Contract

Define an abstract manifest or YAML block that maps source columns to model contract fields.

```yaml
live_table_source:
  catalog: evri_datalakehouse_prod_catalog
  schema: analytics_sandbox
  table: fcast_multi_client_data_build_champion_modelv35

  column_map:
    date:
      source: preadvice_date
      target: event_date
    volume:
      source: parcel_volume
      target: actual_volume
    baseline:
      source: median_4wk_volume
      target: rolling_4w_median
    target:
      source: target
      target: target
    china:
      source: china_flag
      target: is_china
    domestic:
      source: domestic_flag
      target: is_domestic

  push_down_filters:
    lookback_days: 365
    min_baseline_volume: 10
    require_non_null:
      - preadvice_date
      - parcel_volume
      - median_4wk_volume

  guardrail:
    expected_row_count: 124506
    min_row_fraction: 0.50
    max_drop_fraction: 0.92
```

### Stage 2: Push-Down Execution

Use Spark SQL to project only the required columns and filter the dataset before any Pandas conversion.

Stage 2 requirements:

- The execution layer must project only the contracted columns defined in the manifest.
- The execution layer must enforce all temporal and cohort filters in Databricks before collection into driver memory.
- The execution layer must enforce non-null checks for all required training columns at the database tier.
- The execution layer must include strict null-target insulation by requiring the mapped target source column to be non-null before any row is allowed into the training slice.
- The execution layer must continue to exclude rows where the baseline feature is non-positive.
- The execution layer must produce a clean, bounded training slice suitable for downstream Pandas or local XGBoost processing.

Minimum SQL contract for Stage 2 filtering:

- `date IS NOT NULL`
- `volume IS NOT NULL`
- `baseline IS NOT NULL`
- `target IS NOT NULL`
- `baseline > min_baseline_volume`
- `date >= lookback_cutoff`

### Stage 3: Volumetric Guardrail

Use a volumetric compliance guardrail to classify live data quality under CMMI Level 5 quantitative process control, rather than treating every non-failure as equivalent.

Stage 3 requirements:

- The guardrail must compute `drop_frac = 1 - valid_rows / expected_row_count`.
- The guardrail must evaluate the final slice using three operational tolerance zones.

Zone 1: Nominal Operation

- Condition: `drop_frac <= 0.02`
- Required action: log a success message with the drop percentage.
- Outcome: return `passed = True` and `failure_reason = None`.

Zone 2: Approved Contract Deviation

- Condition: `drop_frac > 0.02` while still satisfying:
  - `valid_rows >= expected_row_count * min_row_fraction`
  - `drop_frac <= max_drop_fraction`
- Required action: log an architectural governance warning:
  - `[GOVERNANCE WARNING] Zone 2 Deviation Detected. Proceeding under approved operational tolerance thresholds.`
- Outcome: return `passed = True` and `failure_reason = WARNING: ApprovedSchemaDeviation` so orchestration can track tolerated degradation.

Zone 3: Hard Contract Breach

- Condition: either:
  - `valid_rows < expected_row_count * min_row_fraction`, or
  - `drop_frac > max_drop_fraction`
- Required action: log a critical failure message.
- Outcome:
  - return `passed = False` and `failure_reason = CRITICAL: DataStarvationError` for under-volume starvation, or
  - return `passed = False` and `failure_reason = CRITICAL: DataQualityError` for excessive drop fraction.

Control intent:

- Zone 1 represents stable, in-control operation.
- Zone 2 represents managed variance inside an approved enterprise risk envelope.
- Zone 3 represents a contract breach that must halt training and surface an operational incident.

## Governance Notes

- Treat `analytics_sandbox` as a team-owned analytical workspace, not an automatically trusted gold layer.
- Verify whether `client_name` is a B2B account identifier or a PII-bearing identifier before any production promotion.
- Confirm with the owning team whether `fcast_multi_client_data_build_champion_modelv35` is the authoritative production-grade training source.

## Next Implementation Step

Convert the above manifest and requirements into a config-driven loader in the training codebase so the Spark-side filter, projection, null-target insulation, and three-zone guardrail are enforced before any Pandas collection or model training.