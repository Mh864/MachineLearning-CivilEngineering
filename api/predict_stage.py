from __future__ import annotations

from datetime import datetime
from typing import Any

import joblib
import numpy as np
import pandas as pd


def load_stage_model_artifact(path: str = "models/stage_model.pkl") -> dict[str, Any]:
    return joblib.load(path)


def _tail7(values: list[float] | None) -> np.ndarray:
    if values is None or len(values) < 7:
        return np.zeros(7, dtype=float)
    return np.array(values[-7:], dtype=float)


def _last_scalar(seq: list[float] | None) -> float:
    if not seq:
        return 0.0
    return float(seq[-1])


def _build_stage_feature_frame(
    *,
    feature_cols: list[str],
    date: pd.Timestamp,
    recent_stage: list[float],
    recent_discharge: list[float] | None = None,
    recent_prcp: list[float] | None = None,
    recent_tmax: list[float] | None = None,
    recent_tmin: list[float] | None = None,
) -> pd.DataFrame:
    if len(recent_stage) < 7:
        raise ValueError("Need at least 7 recent stage values (oldest -> newest).")
    s = np.array(recent_stage[-7:], dtype=float)
    q = _tail7(recent_discharge)
    p = _tail7(recent_prcp)

    stage_lag1 = float(s[-2])
    stage_lag2 = float(s[-3])
    stage_lag3 = float(s[-4])
    stage_roll_mean_3 = float(np.mean(s[-3:]))
    stage_roll_mean_7 = float(np.mean(s[-7:]))
    stage_diff_1 = float(s[-1] - s[-2])
    discharge_lag1 = float(q[-2])
    discharge_roll_mean_3 = float(np.mean(q[-3:]))
    month = int(date.month)
    prcp_lag1 = float(p[-2])
    prcp_roll_sum_3 = float(np.sum(p[-3:]))
    prcp_roll_sum_7 = float(np.sum(p[-7:]))
    tmax = _last_scalar(recent_tmax)
    tmin = _last_scalar(recent_tmin)
    tavg = (tmax + tmin) / 2.0
    temp_range = tmax - tmin

    feats: dict[str, float | int] = {
        "stage_lag1": stage_lag1,
        "stage_lag2": stage_lag2,
        "stage_lag3": stage_lag3,
        "stage_roll_mean_3": stage_roll_mean_3,
        "stage_roll_mean_7": stage_roll_mean_7,
        "stage_diff_1": stage_diff_1,
        "discharge_lag1": discharge_lag1,
        "discharge_roll_mean_3": discharge_roll_mean_3,
        "month": month,
        "prcp_lag1": prcp_lag1,
        "prcp_roll_sum_3": prcp_roll_sum_3,
        "prcp_roll_sum_7": prcp_roll_sum_7,
        "tmax": tmax,
        "tmin": tmin,
        "tavg": tavg,
        "temp_range": temp_range,
    }
    row = {c: float(feats.get(c, 0.0)) for c in feature_cols}
    return pd.DataFrame([row])


def predict_next_stage(
    *,
    artifact: dict[str, Any],
    recent_stage: list[float],
    as_of_date: str | None = None,
    recent_discharge: list[float] | None = None,
    recent_prcp: list[float] | None = None,
    recent_tmax: list[float] | None = None,
    recent_tmin: list[float] | None = None,
) -> float:
    model = artifact["model"]
    feature_cols = artifact["feature_columns"]

    if as_of_date is None:
        date = pd.Timestamp(datetime.utcnow().date())
    else:
        date = pd.to_datetime(as_of_date, errors="raise")

    X = _build_stage_feature_frame(
        feature_cols=feature_cols,
        date=date,
        recent_stage=recent_stage,
        recent_discharge=recent_discharge,
        recent_prcp=recent_prcp,
        recent_tmax=recent_tmax,
        recent_tmin=recent_tmin,
    )
    X = X[feature_cols]
    return float(model.predict(X)[0])
