from __future__ import annotations

"""Notebook-launcher POC helper.

This module lets notebooks trigger repository training code on notebook-attached
compute while enforcing debug mode for governance-safe POC runs.
"""

from src.config import DEFAULT_DATASET_VERSION, DEFAULT_EXPERIMENT_NAME
from src.training.train_xgboost import run_training


def run_notebook_launcher_poc(
    input_csv: str = "/dbfs/FileStore/forecasting/multi_client_ib_uplift.csv",
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    dataset_version: str = DEFAULT_DATASET_VERSION,
) -> None:
    """Run repo-backed training from a notebook as a debug-only POC."""
    run_training(
        input_csv=input_csv,
        experiment_name=experiment_name,
        dataset_version=dataset_version,
        run_mode="debug",
    )
