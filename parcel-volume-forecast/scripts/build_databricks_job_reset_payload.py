from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import (
    DATABRICKS_JOB_ID,
    DEFAULT_DATABRICKS_PHASE0_FALLBACK_CLUSTER_ID,
    DEFAULT_DATASET_VERSION,
    DEFAULT_DATABRICKS_WORKSPACE_REPO_ROOT,
    DEFAULT_EXPERIMENT_NAME,
)


def build_payload(cluster_id: str, input_csv: str, workspace_repo_root: str) -> dict:
    python_file = f"{workspace_repo_root.rstrip('/')}/src/training/train_xgboost.py"
    return {
        "job_id": DATABRICKS_JOB_ID,
        "new_settings": {
            "name": "parcel-volume-forecast-train",
            "max_concurrent_runs": 1,
            "tasks": [
                {
                    "task_key": "train_xgboost",
                    "spark_python_task": {
                        "python_file": python_file,
                        "parameters": [
                            "--input-csv",
                            input_csv,
                            "--experiment",
                            DEFAULT_EXPERIMENT_NAME,
                            "--dataset-version",
                            DEFAULT_DATASET_VERSION,
                            "--run-mode",
                            "production",
                        ],
                    },
                    "existing_cluster_id": cluster_id,
                }
            ],
            "schedule": {
                "quartz_cron_expression": "0 0 5 ? * MON",
                "timezone_id": "Europe/London",
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a Databricks jobs reset payload aligned to jobs/train_job.yaml."
    )
    parser.add_argument(
        "--cluster-id",
        default=DEFAULT_DATABRICKS_PHASE0_FALLBACK_CLUSTER_ID,
        help="Existing Databricks cluster id for the training job.",
    )
    parser.add_argument(
        "--input-csv",
        default="/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv",
        help="DBFS path to the training CSV consumed by the Databricks run.",
    )
    parser.add_argument(
        "--workspace-repo-root",
        default=DEFAULT_DATABRICKS_WORKSPACE_REPO_ROOT,
        help="Absolute Databricks workspace repo root that contains this project.",
    )
    parser.add_argument(
        "--output",
        default="databricks-job-reset.json",
        help="Path to write the generated Databricks reset payload JSON.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    payload = build_payload(
        cluster_id=args.cluster_id,
        input_csv=args.input_csv,
        workspace_repo_root=args.workspace_repo_root,
    )
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()