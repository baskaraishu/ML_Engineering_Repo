from __future__ import annotations

"""Evaluation metrics used by Phase 1 forecast model validation.

These functions provide consistent model-quality calculations for run gating
and leadership reporting. They support controlled performance comparisons
against baseline and champion models.
"""

import numpy as np


def smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-9) -> float:
    """Symmetric mean absolute percentage error used in notebook tuning/eval."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred) + eps
    return float(np.mean(2.0 * np.abs(y_pred - y_true) / denom) * 100.0)
