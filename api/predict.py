from __future__ import annotations

from datetime import datetime
from typing import Any

import joblib
import numpy as np
import pandas as pd


def load_model_artifact(path: str = "models/model.pkl") -> dict[str, Any]:
    return joblib.load(path)


def _tail7(values: list[float] | None) -> np.ndarray:
    if values is None or len(values) < 7:
        return np.zeros(7, dtype=float)
    return np.array(values[-7:], dtype=float)


def _last_scalar(seq: list[float] | None) -> float:
    if not seq:
        return 0.0
    return float(seq[-1])


def _build_feature_frame(
    *,
    feature_cols: list[str],
    date: pd.Timestamp,
    recent_discharge: list[float],
    recent_prcp: list[float] | None = None,
    recent_tmax: list[float] | None = None,
    recent_tmin: list[float] | None = None,
    recent_awnd: list[float] | None = None,
    recent_snow: list[float] | None = None,
    recent_snow_depth: list[float] | None = None,
    heavy_rain_threshold: float | None = None,
) -> pd.DataFrame:
    """
    One-row feature frame aligned with modeling/features.py::_add_features_per_site.

    recent_discharge / recent_prcp: seven daily values oldest → newest for days
    D-6 … D (last value = observation on day D, matching merged USGS + NOAA rows).

    Training row for day D uses discharge_lag1 = Q_{D-1} (shift(1)), not Q_D.
    """
    if len(recent_discharge) < 7:
        raise ValueError("Need at least 7 recent discharge values (oldest -> newest).")

    x = np.array(recent_discharge[-7:], dtype=float)
    # Align with sdf["discharge_lag1"] = discharge.shift(1) at row D
    discharge_lag1 = float(x[-2])
    discharge_lag2 = float(x[-3])
    discharge_lag3 = float(x[-4])
    discharge_roll_mean_3 = float(np.mean(x[-3:]))
    discharge_roll_mean_7 = float(np.mean(x[-7:]))
    discharge_roll_std_3 = float(np.std(x[-3:], ddof=1))
    discharge_roll_std_7 = float(np.std(x[-7:], ddof=1))
    discharge_roll_max_3 = float(np.max(x[-3:]))
    discharge_roll_max_7 = float(np.max(x[-7:]))
    discharge_diff_1 = float(x[-1] - x[-2])
    month = int(date.month)
    month_sin = float(np.sin(2.0 * np.pi * month / 12.0))
    month_cos = float(np.cos(2.0 * np.pi * month / 12.0))

    p = _tail7(recent_prcp)

    # prcp_lag1 = prcp.shift(1) at D → precipitation on D-1
    prcp_lag1 = float(p[-2])
    prcp_lag2 = float(p[-3])
    prcp_lag3 = float(p[-4])
    prcp_roll_sum_3 = float(np.sum(p[-3:]))
    prcp_roll_sum_7 = float(np.sum(p))
    prcp_roll_mean_3 = float(np.mean(p[-3:]))
    prcp_roll_mean_7 = float(np.mean(p))

    thr = 20.0 if heavy_rain_threshold is None else float(heavy_rain_threshold)
    # heavy_rain_flag_1d uses same-day prcp at D
    heavy_rain_flag_1d = 1.0 if float(p[-1]) > thr else 0.0
    heavy_idxs = np.where(p > thr)[0]
    if len(heavy_idxs) == 0:
        days_since_last_heavy_rain = float(len(p))
    else:
        days_since_last_heavy_rain = float((len(p) - 1) - int(heavy_idxs[-1]))

    tmax = _last_scalar(recent_tmax)
    tmin = _last_scalar(recent_tmin)
    tavg = (tmax + tmin) / 2.0
    temp_range = tmax - tmin
    awnd = _last_scalar(recent_awnd)
    snow = _last_scalar(recent_snow)
    snow_depth = _last_scalar(recent_snow_depth)

    prcp_x_discharge_lag1 = float(p[-1]) * discharge_lag1
    prcp_roll_sum_3_x_discharge_roll_mean_3 = prcp_roll_sum_3 * discharge_roll_mean_3

    # Legacy 10-col artifacts (precip_mm_*), if present
    precip_mm_lag1 = prcp_lag1
    precip_mm_roll_3 = prcp_roll_sum_3
    precip_mm_roll_7 = prcp_roll_sum_7

    feats: dict[str, float | int] = {
        "discharge_lag1": discharge_lag1,
        "discharge_lag2": discharge_lag2,
        "discharge_lag3": discharge_lag3,
        "discharge_roll_mean_3": discharge_roll_mean_3,
        "discharge_roll_mean_7": discharge_roll_mean_7,
        "discharge_roll_std_3": discharge_roll_std_3,
        "discharge_roll_std_7": discharge_roll_std_7,
        "discharge_roll_max_3": discharge_roll_max_3,
        "discharge_roll_max_7": discharge_roll_max_7,
        "discharge_diff_1": discharge_diff_1,
        "month": month,
        "month_sin": month_sin,
        "month_cos": month_cos,
        "precip_mm_lag1": precip_mm_lag1,
        "precip_mm_roll_3": precip_mm_roll_3,
        "precip_mm_roll_7": precip_mm_roll_7,
        "prcp_lag1": prcp_lag1,
        "prcp_lag2": prcp_lag2,
        "prcp_lag3": prcp_lag3,
        "prcp_roll_sum_3": prcp_roll_sum_3,
        "prcp_roll_sum_7": prcp_roll_sum_7,
        "prcp_roll_mean_3": prcp_roll_mean_3,
        "prcp_roll_mean_7": prcp_roll_mean_7,
        "heavy_rain_flag_1d": heavy_rain_flag_1d,
        "days_since_last_heavy_rain": days_since_last_heavy_rain,
        "tmax": tmax,
        "tmin": tmin,
        "tavg": tavg,
        "temp_range": temp_range,
        "awnd": awnd,
        "snow": snow,
        "snow_depth": snow_depth,
        "prcp_x_discharge_lag1": prcp_x_discharge_lag1,
        "prcp_roll_sum_3_x_discharge_roll_mean_3": prcp_roll_sum_3_x_discharge_roll_mean_3,
    }

    row = {c: float(feats.get(c, 0.0)) for c in feature_cols}
    return pd.DataFrame([row])


def predict_from_recent_discharge(
    *,
    artifact: dict[str, Any],
    recent_discharge: list[float],
    as_of_date: str | None = None,
    recent_prcp: list[float] | None = None,
    recent_tmax: list[float] | None = None,
    recent_tmin: list[float] | None = None,
    recent_awnd: list[float] | None = None,
    recent_snow: list[float] | None = None,
    recent_snow_depth: list[float] | None = None,
    heavy_rain_threshold: float | None = None,
) -> dict[str, Any]:
    model = artifact["model"]
    feature_cols = artifact["feature_columns"]

    if as_of_date is None:
        date = pd.Timestamp(datetime.utcnow().date())
    else:
        date = pd.to_datetime(as_of_date, errors="raise")

    X = _build_feature_frame(
        feature_cols=feature_cols,
        date=date,
        recent_discharge=recent_discharge,
        recent_prcp=recent_prcp,
        recent_tmax=recent_tmax,
        recent_tmin=recent_tmin,
        recent_awnd=recent_awnd,
        recent_snow=recent_snow,
        recent_snow_depth=recent_snow_depth,
        heavy_rain_threshold=heavy_rain_threshold,
    )
    X = X[feature_cols]
    target_type = artifact.get("target_type", "binary")
    best_threshold = artifact.get("best_threshold")
    proba_vec = model.predict_proba(X)[0] if hasattr(model, "predict_proba") else None

    if target_type == "multiclass":
        if proba_vec is None:
            pred = int(model.predict(X)[0])
            return {"prediction": pred, "probability": {"normal": 0.0, "medium": 0.0, "high": 0.0}}
        pred = int(np.argmax(proba_vec))
        return {
            "prediction": pred,
            "probability": {
                "normal": float(proba_vec[0]),
                "medium": float(proba_vec[1]),
                "high": float(proba_vec[2]),
            },
        }

    if proba_vec is not None:
        p1 = float(proba_vec[1])
    else:
        p1 = float(model.predict(X)[0])
    threshold = float(best_threshold) if best_threshold is not None else 0.5
    pred = int(p1 >= threshold)
    return {"prediction": pred, "probability": p1}
