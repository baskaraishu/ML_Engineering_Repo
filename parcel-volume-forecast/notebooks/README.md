# Notebooks

Use `../README.md` for AI workflow context and `../PROJECT_SPEC.md` for project scope.

Notebook usage:
- EDA and Genie-assisted discovery
- Visualization and diagnostics
- SHAP/explainability review

Phase 0 notebook-launcher POC (repo-code execution):
- Notebook can be used as a launcher, but business logic must execute from `src/` modules.
- Use debug-only mode for this path so runs are marked non-production evidence.

Example notebook cell:

```python
from src.training import run_notebook_launcher_poc

run_notebook_launcher_poc(
	input_csv="/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv",
	experiment_name="/Shared/forecasting/parcel-volume-forecast",
	dataset_version="v1-poc",
)
```

Promote stable/reused logic into `src/` and run it via Workflows in `jobs/`.
