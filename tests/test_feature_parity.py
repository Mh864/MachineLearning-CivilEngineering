"""
Step 3: training vs API feature parity.

Ensures `api.predict._build_feature_frame` matches `modeling.features._add_features_per_site`
for the same 7-day discharge + weather window (guards drift when FEATURE_COLUMNS or inference changes).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def paths_exist() -> bool:
    clean = ROOT / "data/processed/clean_data.csv"
    noaa = ROOT / "data/raw/noaa"
    return clean.is_file() and noaa.is_dir()


def test_inference_matches_training_row(paths_exist: bool) -> None:
    if not paths_exist:
        pytest.skip("Need data/processed/clean_data.csv and data/raw/noaa/ for parity test")

    from api.predict import _build_feature_frame
    from modeling.features import (
        FEATURE_COLUMNS,
        _add_features_per_site,
        load_noaa_weather,
        merge_weather_into_site_discharge,
    )

    df = pd.read_csv(ROOT / "data/processed/clean_data.csv", dtype={"site_id": "string"})
    df["site_id"] = df["site_id"].astype("string").str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["discharge"] = pd.to_numeric(df["discharge"], errors="coerce")
    df = df.dropna(subset=["site_id", "date", "discharge"])

    noaa_df, _ = load_noaa_weather(ROOT / "data/raw/noaa")

    site_id: str | None = None
    sdf: pd.DataFrame | None = None
    weather_site: pd.DataFrame | None = None
    Dn: pd.Timestamp | None = None

    for sid, sdf_g in df.groupby("site_id", sort=True):
        if len(sdf_g) < 14:
            continue
        w_site = None
        if not noaa_df.empty:
            w = noaa_df.loc[
                noaa_df["site_id"] == str(sid),
                ["date", "prcp", "tmax", "tmin", "awnd", "snow", "snwd"],
            ]
            if not w.empty:
                w_site = w
        merged_try = merge_weather_into_site_discharge(sdf_g[["date", "discharge"]].copy(), w_site)
        if len(merged_try) < 8:
            continue
        idx_row = 7
        D_try = merged_try.iloc[idx_row]["date"]
        Dn_try = pd.Timestamp(D_try).normalize()
        feat_try = _add_features_per_site(
            sdf_g[["date", "discharge"]].copy(),
            precip_df=w_site,
            heavy_rain_threshold=20.0,
        )
        feat_try["date"] = pd.to_datetime(feat_try["date"]).dt.normalize()
        if feat_try.loc[feat_try["date"] == Dn_try, FEATURE_COLUMNS].empty:
            continue
        site_id = str(sid)
        sdf = sdf_g
        weather_site = w_site
        Dn = Dn_try
        break

    if site_id is None or sdf is None or Dn is None:
        pytest.skip("No suitable site/window in clean_data for parity test")

    feat_full = _add_features_per_site(
        sdf[["date", "discharge"]].copy(),
        precip_df=weather_site,
        heavy_rain_threshold=20.0,
    )
    feat_full["date"] = pd.to_datetime(feat_full["date"]).dt.normalize()
    training_row = feat_full.loc[feat_full["date"] == Dn, FEATURE_COLUMNS]
    if training_row.empty:
        pytest.skip(f"No engineered row for date {Dn} (likely dropped by NaNs)")
    training_row = training_row.iloc[0]

    merged = merge_weather_into_site_discharge(sdf[["date", "discharge"]].copy(), weather_site)
    merged = merged.reset_index(drop=True)
    merged["date"] = pd.to_datetime(merged["date"]).dt.normalize()
    hit = merged[merged["date"] == Dn]
    assert not hit.empty, "date D not in merged frame"
    idx = int(hit.index[0])
    wdf = merged.iloc[idx - 6 : idx + 1]
    assert len(wdf) == 7, "expected 7 consecutive days"

    recent_discharge = wdf["discharge"].astype(float).tolist()
    recent_prcp = wdf["prcp"].astype(float).tolist()
    recent_tmax = wdf["tmax"].astype(float).tolist()
    recent_tmin = wdf["tmin"].astype(float).tolist()
    recent_awnd = wdf["awnd"].astype(float).tolist()
    recent_snow = wdf["snow"].astype(float).tolist()
    recent_snow_depth = wdf["snow_depth"].astype(float).tolist()

    api_df = _build_feature_frame(
        feature_cols=list(FEATURE_COLUMNS),
        date=Dn,
        recent_discharge=recent_discharge,
        recent_prcp=recent_prcp,
        recent_tmax=recent_tmax,
        recent_tmin=recent_tmin,
        recent_awnd=recent_awnd,
        recent_snow=recent_snow,
        recent_snow_depth=recent_snow_depth,
        heavy_rain_threshold=20.0,
    )

    for col in FEATURE_COLUMNS:
        a = float(api_df[col].iloc[0])
        b = float(training_row[col])
        np.testing.assert_allclose(a, b, rtol=1e-5, atol=1e-4, err_msg=f"mismatch on {col}")
