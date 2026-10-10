from __future__ import annotations

"""Model-construction helpers for the training pipeline."""

from xgboost import XGBRegressor

from src.config import (
    XGB_COLSAMPLE_BYTREE,
    XGB_LEARNING_RATE,
    XGB_MAX_DEPTH,
    XGB_N_ESTIMATORS,
    XGB_RANDOM_STATE,
    XGB_SUBSAMPLE,
)


def build_xgb_regressor() -> XGBRegressor:
    """Create the configured XGBoost regressor for uplift training."""
    return XGBRegressor(
        n_estimators=XGB_N_ESTIMATORS,
        max_depth=XGB_MAX_DEPTH,
        learning_rate=XGB_LEARNING_RATE,
        subsample=XGB_SUBSAMPLE,
        colsample_bytree=XGB_COLSAMPLE_BYTREE,
        objective="reg:squarederror",
        random_state=XGB_RANDOM_STATE,
    )