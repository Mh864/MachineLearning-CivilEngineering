from __future__ import annotations

from datetime import datetime
from typing import Any

import joblib
import numpy as np
import pandas as pd


def load_model_artifact(path: str = "models/model.pkl") -> dict[str, Any]:
    return joblib.load(path)


def _compute_features_from_recent(date: pd.Timestamp, recent: list[float]) -> pd.DataFrame:
    """
    Build the same feature set as `modeling/features.py` from recent discharge values.

    recent must be ordered oldest -> newest and contain at least 7 values.
    """
    if len(recent) < 7:
        raise ValueError("Need at least 7 recent discharge values (oldest -> newest).")

    x = np.array(recent, dtype=float)
    lag1 = float(x[-1])
    lag2 = float(x[-2])
    lag3 = float(x[-3])

    roll3 = float(np.mean(x[-3:]))
    roll7 = float(np.mean(x[-7:]))
    diff1 = float(lag1 - lag2)

    month = int(date.month)

    return pd.DataFrame(
        [
            {
                "discharge_lag1": lag1,
                "discharge_lag2": lag2,
                "discharge_lag3": lag3,
                "discharge_roll_mean_3": roll3,
                "discharge_roll_mean_7": roll7,
                "discharge_diff_1": diff1,
                "month": month,
            }
        ]
    )


def predict_from_recent_discharge(
    *,
    artifact: dict[str, Any],
    recent_discharge: list[float],
    as_of_date: str | None = None,
) -> int:
    model = artifact["model"]
    feature_cols = artifact["feature_columns"]

    if as_of_date is None:
        date = pd.Timestamp(datetime.utcnow().date())
    else:
        date = pd.to_datetime(as_of_date, errors="raise")

    X = _compute_features_from_recent(date, recent_discharge)
    X = X[feature_cols]
    pred = model.predict(X)[0]
    return int(pred)

