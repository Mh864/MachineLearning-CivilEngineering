from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SITE_TO_NOAA = {
    "01646500": "Potomac_DC",
    "02087500": "Neuse_NC",
    "03015500": "Allegheny_PA",
    "05054000": "RedRiver_ND",
    "06710247": "CherryCreek_CO",
    "08066500": "Trinity_TX",
    "09380000": "Colorado_AZ",
    "11447650": "Sacramento_CA",
    "12301933": "ClarkFork_MT",
    "14211720": "Willamette_OR",
}


FEATURE_COLUMNS = [
    "discharge_lag1",
    "discharge_lag2",
    "discharge_lag3",
    "discharge_roll_mean_3",
    "discharge_roll_mean_7",
    "discharge_diff_1",
    "month",
    "precip_mm_lag1",
    "precip_mm_roll_3",
    "precip_mm_roll_7",
]


def load_noaa_precip(noaa_dir: str | Path) -> dict[str, pd.DataFrame]:
    noaa_dir = Path(noaa_dir)
    if not noaa_dir.exists():
        return {}

    out: dict[str, pd.DataFrame] = {}
    for fp in sorted(noaa_dir.glob("rainfall_*.csv")):
        location_name = fp.stem.replace("rainfall_", "", 1)
        df = pd.read_csv(fp)
        if "DATE" not in df.columns or "PRCP" not in df.columns:
            continue

        p = pd.DataFrame(
            {
                "date": pd.to_datetime(df["DATE"], errors="coerce"),
                "precip_mm": pd.to_numeric(df["PRCP"], errors="coerce").fillna(0.0),
            }
        )
        p = p.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        out[location_name] = p
    return out


def _add_features_per_site(sdf: pd.DataFrame, precip_df: pd.DataFrame | None = None) -> pd.DataFrame:
    sdf = sdf.sort_values("date").copy()

    if precip_df is not None:
        p = precip_df.copy()
        p["date"] = pd.to_datetime(p["date"], errors="coerce")
        p["precip_mm"] = pd.to_numeric(p["precip_mm"], errors="coerce").fillna(0.0)
        p = p.dropna(subset=["date"])
        sdf = sdf.merge(p[["date", "precip_mm"]], on="date", how="left")
        sdf["precip_mm"] = pd.to_numeric(sdf["precip_mm"], errors="coerce").fillna(0.0)
        sdf["precip_mm_lag1"] = sdf["precip_mm"].shift(1)
        sdf["precip_mm_roll_3"] = sdf["precip_mm"].rolling(3, min_periods=1).sum()
        sdf["precip_mm_roll_7"] = sdf["precip_mm"].rolling(7, min_periods=1).sum()
    else:
        sdf["precip_mm_lag1"] = 0.0
        sdf["precip_mm_roll_3"] = 0.0
        sdf["precip_mm_roll_7"] = 0.0

    sdf["discharge_lag1"] = sdf["discharge"].shift(1)
    sdf["discharge_lag2"] = sdf["discharge"].shift(2)
    sdf["discharge_lag3"] = sdf["discharge"].shift(3)

    sdf["discharge_roll_mean_3"] = sdf["discharge"].rolling(window=3, min_periods=3).mean()
    sdf["discharge_roll_mean_7"] = sdf["discharge"].rolling(window=7, min_periods=7).mean()

    sdf["discharge_diff_1"] = sdf["discharge"] - sdf["discharge_lag1"]
    sdf["month"] = sdf["date"].dt.month.astype(int)
    return sdf


def _add_target_per_site(sdf: pd.DataFrame, *, percentile: float = 0.9) -> pd.DataFrame:
    sdf = sdf.sort_values("date").copy()

    threshold = float(np.nanpercentile(sdf["discharge"].to_numpy(dtype=float), percentile * 100))
    sdf["threshold"] = threshold

    sdf["discharge_next_day"] = sdf["discharge"].shift(-1)
    has_next = sdf["discharge_next_day"].notna()
    sdf["target"] = np.where(has_next, (sdf["discharge_next_day"] > threshold).astype(int), np.nan)
    return sdf


def build_features_dataset(
    *,
    clean_path: str | Path = "data/processed/clean_data.csv",
    out_path: str | Path = "data/processed/features.csv",
    percentile: float = 0.9,
    noaa_dir: str | Path = "data/raw/noaa",
) -> Path:
    df = pd.read_csv(clean_path, dtype={"site_id": "string"})
    required = {"site_id", "date", "discharge"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in clean_data: {missing}")

    df["site_id"] = df["site_id"].astype("string").str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["discharge"] = pd.to_numeric(df["discharge"], errors="coerce")
    df = df.dropna(subset=["site_id", "date"]).sort_values(["site_id", "date"]).reset_index(drop=True)
    noaa_by_location = load_noaa_precip(noaa_dir)

    parts: list[pd.DataFrame] = []
    for site_id, sdf in df.groupby("site_id", sort=True):
        location_name = SITE_TO_NOAA.get(str(site_id))
        precip_df = noaa_by_location.get(location_name) if location_name is not None else None
        sdf = _add_features_per_site(sdf, precip_df=precip_df)
        sdf = _add_target_per_site(sdf, percentile=percentile)
        sdf["site_id"] = site_id
        parts.append(sdf)

    out = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()

    # Drop rows with NaNs introduced by lags/rolling/shift
    out = out.dropna(subset=FEATURE_COLUMNS + ["target"])

    out_cols = ["site_id", "date"] + FEATURE_COLUMNS + ["threshold", "discharge_next_day", "target"]
    out = out[out_cols].sort_values(["site_id", "date"]).reset_index(drop=True)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate feature matrix and binary target from clean_data.csv.")
    p.add_argument("--clean-path", type=str, default="data/processed/clean_data.csv", help="Input clean dataset CSV")
    p.add_argument("--out-path", type=str, default="data/processed/features.csv", help="Output features CSV")
    p.add_argument("--percentile", type=float, default=0.9, help="Per-site discharge percentile threshold for target (e.g., 0.9)")
    p.add_argument("--noaa-dir", type=str, default="data/raw/noaa", help="Directory containing NOAA rainfall_*.csv files")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    out = build_features_dataset(
        clean_path=args.clean_path,
        out_path=args.out_path,
        percentile=args.percentile,
        noaa_dir=args.noaa_dir,
    )
    print(f"Wrote features dataset: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

