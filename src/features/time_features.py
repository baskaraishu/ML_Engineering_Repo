from __future__ import annotations

"""Time-based feature engineering for forecast seasonality patterns.

Adds cyclical encodings for calendar fields used by the uplift model so
periodic behavior can be learned without notebook-only feature logic.
This module documents the feature-engineering contract for reproducible
Phase 1 training and scoring.
"""

import numpy as np
import pandas as pd


def add_cyclical_time_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Add cyclical time encodings used by the uplift notebook."""
    out = df.copy()
    d = pd.to_datetime(out[date_col])

    out["month"] = d.dt.month
    out["day_of_week"] = d.dt.dayofweek
    out["day_of_year"] = d.dt.dayofyear
    out["week_of_year"] = d.dt.isocalendar().week.astype(int)
    out["day_of_month"] = d.dt.day

    def _sin_cos(series: pd.Series, period: int, prefix: str) -> None:
        out[f"{prefix}_sin"] = np.sin(2 * np.pi * series / period)
        out[f"{prefix}_cos"] = np.cos(2 * np.pi * series / period)

    _sin_cos(out["month"], 12, "month")
    _sin_cos(out["day_of_week"], 7, "dow")
    _sin_cos(out["day_of_year"], 365, "doy")
    _sin_cos(out["week_of_year"], 52, "woy")
    _sin_cos(out["day_of_month"], 31, "dom")

    return out
