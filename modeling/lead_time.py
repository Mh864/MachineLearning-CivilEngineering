from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from modeling.evaluate import _metrics
from modeling.features import FEATURE_COLUMNS, SITE_TO_NOAA, _add_features_per_site, load_noaa_precip
from modeling.utils import time_based_split


def analyze_lead_times(
    *,
    clean_path: str | Path = "data/processed/clean_data.csv",
    model_path: str | Path = "models/lgbm_model.pkl",
    noaa_dir: str | Path = "data/raw/noaa",
    lead_days: list[int] = None,
    out_path: str | Path = "results/lead_time_analysis.json",
) -> Path:
    if lead_days is None:
        lead_days = [1, 2, 3, 5, 7]

    df = pd.read_csv(clean_path, dtype={"site_id": "string"})
    required = {"site_id", "date", "discharge"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in clean_data: {missing}")

    df["site_id"] = df["site_id"].astype("string").str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["discharge"] = pd.to_numeric(df["discharge"], errors="coerce")
    df = df.dropna(subset=["site_id", "date"]).sort_values(["site_id", "date"]).reset_index(drop=True)

    artifact = joblib.load(model_path)
    model = artifact["model"]
    feature_cols = artifact.get("feature_columns", FEATURE_COLUMNS)
    noaa_by_location = load_noaa_precip(noaa_dir)

    results: dict[str, object] = {}
    f1_by_lead: dict[int, float] = {}

    for lead in lead_days:
        parts: list[pd.DataFrame] = []
        for site_id, sdf in df.groupby("site_id", sort=True):
            location_name = SITE_TO_NOAA.get(str(site_id))
            precip_df = noaa_by_location.get(location_name) if location_name is not None else None
            xdf = _add_features_per_site(sdf, precip_df=precip_df)

            threshold = float(np.nanpercentile(xdf["discharge"].to_numpy(dtype=float), 90.0))
            xdf["threshold"] = threshold
            xdf["discharge_future"] = xdf["discharge"].shift(-lead)
            has_future = xdf["discharge_future"].notna()
            xdf["target"] = np.where(has_future, (xdf["discharge_future"] > threshold).astype(int), np.nan)
            xdf["site_id"] = site_id
            parts.append(xdf)

        feat = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
        feat = feat.dropna(subset=list(feature_cols) + ["target"]).sort_values(["site_id", "date"]).reset_index(drop=True)
        feat = feat[["site_id", "date"] + list(feature_cols) + ["target"]]

        split = time_based_split(feat, time_col="date", target_col="target", train_frac=0.70, val_frac=0.15)
        X_test = split.X_test[list(feature_cols)]
        y_test = split.y_test.astype(int)
        y_pred = model.predict(X_test)
        m = _metrics(y_test, y_pred)
        results[f"lead_day_{lead}"] = m
        f1_by_lead[lead] = m["f1"]
        print(f"lead_day_{lead}: {json.dumps(m)}")

    if 1 in f1_by_lead and 7 in f1_by_lead:
        summary = f"F1 degrades from {f1_by_lead[1]:.4f} at 1-day to {f1_by_lead[7]:.4f} at 7-day forecast horizon"
    else:
        first = lead_days[0]
        last = lead_days[-1]
        summary = f"F1 changes from {f1_by_lead[first]:.4f} at {first}-day to {f1_by_lead[last]:.4f} at {last}-day forecast horizon"
    results["summary"] = summary
    print(summary)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Analyze model performance across lead-time horizons.")
    p.add_argument("--clean-path", type=str, default="data/processed/clean_data.csv")
    p.add_argument("--model-path", type=str, default="models/lgbm_model.pkl")
    p.add_argument("--out-path", type=str, default="results/lead_time_analysis.json")
    p.add_argument("--noaa-dir", type=str, default="data/raw/noaa", help="Directory with rainfall_*.csv for feature rebuild")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    out = analyze_lead_times(
        clean_path=args.clean_path,
        model_path=args.model_path,
        noaa_dir=args.noaa_dir,
        out_path=args.out_path,
    )
    print(f"Wrote lead-time analysis: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
