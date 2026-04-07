from __future__ import annotations

from datetime import datetime
from typing import Any

import joblib
import numpy as np
import pandas as pd


def load_model_artifact(path: str = "models/model.pkl") -> dict[str, Any]:
    return joblib.load(path)


def _parse_optional_recent_series(value: str | None, *, n: int) -> np.ndarray:
    if value is None or value.strip() == "":
        return np.zeros(n, dtype=float)

    out = [float(x.strip()) for x in value.split(",") if x.strip() != ""]
    if len(out) < 7:
        raise ValueError("If provided, recent_prcp must contain at least 7 values (oldest -> newest).")
    return np.array(out, dtype=float)


def _compute_features_from_recent(
    date: pd.Timestamp,
    recent: list[float],
    *,
    recent_prcp: str | None = None,
    tmax: float | None = None,
    tmin: float | None = None,
    awnd: float | None = None,
    snow: float | None = None,
    snow_depth: float | None = None,
    heavy_rain_threshold: float = 20.0,
) -> pd.DataFrame:
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
    prcp_arr = _parse_optional_recent_series(recent_prcp, n=len(x))
    prcp = float(prcp_arr[-1])
    prcp_lag1 = float(prcp_arr[-2]) if len(prcp_arr) >= 2 else 0.0
    prcp_lag2 = float(prcp_arr[-3]) if len(prcp_arr) >= 3 else 0.0
    prcp_lag3 = float(prcp_arr[-4]) if len(prcp_arr) >= 4 else 0.0
    prcp_roll_sum_3 = float(np.sum(prcp_arr[-3:]))
    prcp_roll_sum_7 = float(np.sum(prcp_arr[-7:]))
    prcp_roll_mean_3 = float(np.mean(prcp_arr[-3:]))
    prcp_roll_mean_7 = float(np.mean(prcp_arr[-7:]))
    heavy_rain_flag_1d = int(prcp > float(heavy_rain_threshold))

    tmax_v = float(0.0 if tmax is None else tmax)
    tmin_v = float(0.0 if tmin is None else tmin)
    awnd_v = float(0.0 if awnd is None else awnd)
    snow_v = float(0.0 if snow is None else snow)
    snow_depth_v = float(0.0 if snow_depth is None else snow_depth)
    tavg = float((tmax_v + tmin_v) / 2.0)
    temp_range = float(tmax_v - tmin_v)

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
                "prcp_lag1": prcp_lag1,
                "prcp_lag2": prcp_lag2,
                "prcp_lag3": prcp_lag3,
                "prcp_roll_sum_3": prcp_roll_sum_3,
                "prcp_roll_sum_7": prcp_roll_sum_7,
                "prcp_roll_mean_3": prcp_roll_mean_3,
                "prcp_roll_mean_7": prcp_roll_mean_7,
                "heavy_rain_flag_1d": heavy_rain_flag_1d,
                "tmax": tmax_v,
                "tmin": tmin_v,
                "tavg": tavg,
                "temp_range": temp_range,
                "awnd": awnd_v,
                "snow": snow_v,
                "snow_depth": snow_depth_v,
                "prcp_x_discharge_lag1": float(prcp * lag1),
                "prcp_roll_sum_3_x_discharge_roll_mean_3": float(prcp_roll_sum_3 * roll3),
            }
        ]
    )


def predict_from_recent_discharge(
    *,
    artifact: dict[str, Any],
    recent_discharge: list[float],
    as_of_date: str | None = None,
    recent_prcp: str | None = None,
    tmax: float | None = None,
    tmin: float | None = None,
    awnd: float | None = None,
    snow: float | None = None,
    snow_depth: float | None = None,
    heavy_rain_threshold: float = 20.0,
) -> int:
    model = artifact["model"]
    feature_cols = artifact["feature_columns"]

    if as_of_date is None:
        date = pd.Timestamp(datetime.utcnow().date())
    else:
        date = pd.to_datetime(as_of_date, errors="raise")

    X = _compute_features_from_recent(
        date,
        recent_discharge,
        recent_prcp=recent_prcp,
        tmax=tmax,
        tmin=tmin,
        awnd=awnd,
        snow=snow,
        snow_depth=snow_depth,
        heavy_rain_threshold=heavy_rain_threshold,
    )
    X = X[feature_cols]
    pred = model.predict(X)[0]
    return int(pred)

