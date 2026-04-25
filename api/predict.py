from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

_SITE_STATS_CACHE: dict[str, tuple[float, float, float]] | None = None
_SITE_STATS_MTIME: float = 0.0


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


def _normalize_site_id_key(site_id: str) -> str:
    return str(int(str(site_id).strip())).zfill(8)


def _load_site_stats(features_path: str = "data/processed/features.csv") -> dict[str, tuple[float, float, float]]:
    global _SITE_STATS_CACHE, _SITE_STATS_MTIME
    features_file = Path(features_path)
    mtime = 0.0
    try:
        mtime = float(features_file.stat().st_mtime)
    except Exception:
        mtime = 0.0
    if _SITE_STATS_CACHE is not None and mtime <= _SITE_STATS_MTIME:
        return _SITE_STATS_CACHE

    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    required = {"site_id", "site_median", "threshold_medium", "threshold_high"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required site-threshold columns in {features_path}: {sorted(missing)}")

    dedup = (
        df[["site_id", "site_median", "threshold_medium", "threshold_high"]]
        .dropna(subset=["site_id"])
        .copy()
    )
    dedup["site_id"] = dedup["site_id"].astype("string").str.strip().map(_normalize_site_id_key)
    dedup = dedup.drop_duplicates(subset=["site_id"], keep="last")

    stats: dict[str, tuple[float, float, float]] = {}
    for _, row in dedup.iterrows():
        site_median = float(pd.to_numeric(row["site_median"], errors="coerce"))
        p75 = float(pd.to_numeric(row["threshold_medium"], errors="coerce"))
        p90 = float(pd.to_numeric(row["threshold_high"], errors="coerce"))
        stats[str(row["site_id"])] = (site_median, p75, p90)

    _SITE_STATS_CACHE = stats
    _SITE_STATS_MTIME = mtime
    return stats


def _build_feature_frame(
    *,
    site_id: str,
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
    site_key = _normalize_site_id_key(site_id)
    site_stats = _load_site_stats()
    if site_key not in site_stats:
        raise ValueError(f"No per-site thresholds found for site_id={site_id!r} in data/processed/features.csv")
    site_median, site_p75, site_p90 = site_stats[site_key]
    median_denom = site_median if np.isfinite(site_median) and site_median > 0 else 1.0
    p75_denom = site_p75 if np.isfinite(site_p75) and site_p75 > 0 else 1.0
    p90_denom = site_p90 if np.isfinite(site_p90) and site_p90 > 0 else 1.0

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
    discharge_norm_median = float(discharge_lag1 / median_denom)
    discharge_lag1_norm = float(discharge_lag1 / median_denom)
    discharge_lag2_norm = float(discharge_lag2 / median_denom)
    discharge_lag3_norm = float(discharge_lag3 / median_denom)
    discharge_roll_mean_3_norm = float(discharge_roll_mean_3 / median_denom)
    discharge_roll_mean_7_norm = float(discharge_roll_mean_7 / median_denom)
    discharge_pct_of_p75 = float(discharge_lag1 / p75_denom)
    discharge_pct_of_p90 = float(discharge_lag1 / p90_denom)
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
        "discharge_norm_median": discharge_norm_median,
        "discharge_lag1_norm": discharge_lag1_norm,
        "discharge_lag2_norm": discharge_lag2_norm,
        "discharge_lag3_norm": discharge_lag3_norm,
        "discharge_roll_mean_3_norm": discharge_roll_mean_3_norm,
        "discharge_roll_mean_7_norm": discharge_roll_mean_7_norm,
        "discharge_pct_of_p75": discharge_pct_of_p75,
        "discharge_pct_of_p90": discharge_pct_of_p90,
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
    site_id: str,
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
        site_id=site_id,
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
