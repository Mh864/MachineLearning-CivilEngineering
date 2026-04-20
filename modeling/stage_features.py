from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modeling.features import load_noaa_weather


STAGE_FEATURE_COLUMNS = [
    "stage_lag1",
    "stage_lag2",
    "stage_lag3",
    "stage_roll_mean_3",
    "stage_roll_mean_7",
    "stage_diff_1",
    "discharge_lag1",
    "discharge_roll_mean_3",
    "month",
    "prcp_lag1",
    "prcp_roll_sum_3",
    "prcp_roll_sum_7",
    "tmax",
    "tmin",
    "tavg",
    "temp_range",
]


def _add_stage_features_per_site(sdf: pd.DataFrame, weather_site: pd.DataFrame | None) -> pd.DataFrame:
    sdf = sdf.sort_values("date").copy()
    if weather_site is not None and not weather_site.empty:
        ws = weather_site.copy()
        ws["date"] = pd.to_datetime(ws["date"], errors="coerce")
        for c in ["prcp", "tmax", "tmin"]:
            if c not in ws.columns:
                ws[c] = pd.NA
            ws[c] = pd.to_numeric(ws[c], errors="coerce")
        ws = ws.dropna(subset=["date"])
        sdf = sdf.merge(ws[["date", "prcp", "tmax", "tmin"]], on="date", how="left")
    else:
        sdf["prcp"] = pd.NA
        sdf["tmax"] = pd.NA
        sdf["tmin"] = pd.NA

    sdf["prcp"] = pd.to_numeric(sdf["prcp"], errors="coerce").fillna(0.0)
    sdf["tmax"] = pd.to_numeric(sdf["tmax"], errors="coerce").fillna(0.0)
    sdf["tmin"] = pd.to_numeric(sdf["tmin"], errors="coerce").fillna(0.0)
    sdf["tavg"] = (sdf["tmax"] + sdf["tmin"]) / 2.0
    sdf["temp_range"] = sdf["tmax"] - sdf["tmin"]

    sdf["stage_lag1"] = sdf["stage"].shift(1)
    sdf["stage_lag2"] = sdf["stage"].shift(2)
    sdf["stage_lag3"] = sdf["stage"].shift(3)
    sdf["stage_roll_mean_3"] = sdf["stage"].rolling(window=3, min_periods=3).mean()
    sdf["stage_roll_mean_7"] = sdf["stage"].rolling(window=7, min_periods=7).mean()
    sdf["stage_diff_1"] = sdf["stage"] - sdf["stage_lag1"]

    sdf["discharge_lag1"] = sdf["discharge"].shift(1)
    sdf["discharge_roll_mean_3"] = sdf["discharge"].rolling(window=3, min_periods=3).mean()

    sdf["month"] = sdf["date"].dt.month.astype(int)
    sdf["prcp_lag1"] = sdf["prcp"].shift(1)
    sdf["prcp_roll_sum_3"] = sdf["prcp"].rolling(window=3, min_periods=1).sum()
    sdf["prcp_roll_sum_7"] = sdf["prcp"].rolling(window=7, min_periods=1).sum()

    sdf["stage_next_day"] = sdf["stage"].shift(-1)
    return sdf


def build_stage_features_dataset(
    *,
    clean_path: str | Path = "data/processed/clean_data.csv",
    out_path: str | Path = "data/processed/stage_features.csv",
    noaa_dir: str | Path = "data/raw/noaa",
) -> Path:
    df = pd.read_csv(clean_path, dtype={"site_id": "string"})
    required = {"site_id", "date", "discharge", "stage"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in clean_data for stage modeling: {missing}")

    df["site_id"] = df["site_id"].astype("string").str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["discharge"] = pd.to_numeric(df["discharge"], errors="coerce")
    df["stage"] = pd.to_numeric(df["stage"], errors="coerce")
    df = df.dropna(subset=["site_id", "date", "discharge", "stage"]).sort_values(["site_id", "date"]).reset_index(drop=True)

    noaa_df, _ = load_noaa_weather(noaa_dir)
    parts: list[pd.DataFrame] = []
    for site_id, sdf in df.groupby("site_id", sort=True):
        weather_site = None
        if not noaa_df.empty:
            weather_site = noaa_df.loc[noaa_df["site_id"] == str(site_id), ["date", "prcp", "tmax", "tmin"]]
            if weather_site.empty:
                weather_site = None
        fe = _add_stage_features_per_site(sdf, weather_site)
        fe["site_id"] = site_id
        parts.append(fe)

    out = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    out = out.dropna(subset=STAGE_FEATURE_COLUMNS + ["stage_next_day"])
    out_cols = ["site_id", "date"] + STAGE_FEATURE_COLUMNS + ["stage_next_day"]
    out = out[out_cols].sort_values(["site_id", "date"]).reset_index(drop=True)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate stage regression features from clean_data.csv.")
    p.add_argument("--clean-path", type=str, default="data/processed/clean_data.csv")
    p.add_argument("--out-path", type=str, default="data/processed/stage_features.csv")
    p.add_argument("--noaa-dir", type=str, default="data/raw/noaa")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    out = build_stage_features_dataset(clean_path=args.clean_path, out_path=args.out_path, noaa_dir=args.noaa_dir)
    print(f"Wrote stage features dataset: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
