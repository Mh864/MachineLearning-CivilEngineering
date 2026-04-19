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
    "11425500": "Sacramento_CA",
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
    "prcp_lag1",
    "prcp_lag2",
    "prcp_lag3",
    "prcp_roll_sum_3",
    "prcp_roll_sum_7",
    "prcp_roll_mean_3",
    "prcp_roll_mean_7",
    "heavy_rain_flag_1d",
    "tmax",
    "tmin",
    "tavg",
    "temp_range",
    "awnd",
    "snow",
    "snow_depth",
    "prcp_x_discharge_lag1",
    "prcp_roll_sum_3_x_discharge_roll_mean_3",
]


def load_noaa_precip(noaa_dir: str | Path) -> dict[str, pd.DataFrame]:
    """
    Backward-compatible helper used by lead_time analysis.
    Returns location_name -> [date, precip_mm] from rainfall_*.csv files.
    """
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


def load_noaa_weather(noaa_dir: str | Path) -> tuple[pd.DataFrame, set[str]]:
    """
    Load NOAA weather data from `noaa_daily_*.csv` and/or `rainfall_*.csv`.
    Returns normalized dataframe with columns:
      site_id, date, prcp, tmax, tmin, awnd, snow, snwd
    """
    noaa_dir = Path(noaa_dir)
    if not noaa_dir.exists():
        empty = pd.DataFrame(columns=["site_id", "date", "prcp", "tmax", "tmin", "awnd", "snow", "snwd"])
        return empty, set()

    reverse_map = {v: k for k, v in SITE_TO_NOAA.items()}
    frames: list[pd.DataFrame] = []
    available_inputs: set[str] = set()

    def _first_existing(df: pd.DataFrame, choices: list[str]) -> pd.Series:
        for c in choices:
            if c in df.columns:
                return df[c]
        return pd.Series([pd.NA] * len(df))

    for fp in sorted(noaa_dir.glob("*.csv")):
        raw = pd.read_csv(fp)
        if raw.empty:
            continue

        stem = fp.stem
        if stem.startswith("rainfall_"):
            location_name = stem.replace("rainfall_", "", 1)
            site_id = reverse_map.get(location_name)
            if site_id is None:
                continue
            df = raw.copy()
            out = pd.DataFrame(
                {
                    "site_id": site_id,
                    "date": pd.to_datetime(_first_existing(df, ["DATE", "date"]), errors="coerce"),
                    "prcp": pd.to_numeric(_first_existing(df, ["PRCP", "precip_mm", "prcp"]), errors="coerce"),
                    "tmax": pd.to_numeric(_first_existing(df, ["TMAX", "tmax", "tmax_c"]), errors="coerce"),
                    "tmin": pd.to_numeric(_first_existing(df, ["TMIN", "tmin", "tmin_c"]), errors="coerce"),
                    "awnd": pd.to_numeric(_first_existing(df, ["AWND", "awnd"]), errors="coerce"),
                    "snow": pd.to_numeric(_first_existing(df, ["SNOW", "snow"]), errors="coerce"),
                    "snwd": pd.to_numeric(_first_existing(df, ["SNWD", "snow_depth", "snwd"]), errors="coerce"),
                }
            )
        else:
            if "site_id" not in raw.columns:
                continue
            df = raw.copy()
            out = pd.DataFrame(
                {
                    "site_id": df["site_id"].astype("string"),
                    "date": pd.to_datetime(_first_existing(df, ["date", "DATE"]), errors="coerce"),
                    "prcp": pd.to_numeric(_first_existing(df, ["precip_mm", "PRCP", "prcp"]), errors="coerce"),
                    "tmax": pd.to_numeric(_first_existing(df, ["tmax_c", "TMAX", "tmax"]), errors="coerce"),
                    "tmin": pd.to_numeric(_first_existing(df, ["tmin_c", "TMIN", "tmin"]), errors="coerce"),
                    "awnd": pd.to_numeric(_first_existing(df, ["awnd", "AWND"]), errors="coerce"),
                    "snow": pd.to_numeric(_first_existing(df, ["snow", "SNOW"]), errors="coerce"),
                    "snwd": pd.to_numeric(_first_existing(df, ["snwd", "snow_depth", "SNWD"]), errors="coerce"),
                }
            )

        if out["prcp"].notna().any():
            available_inputs.add("PRCP")
        if out["tmax"].notna().any():
            available_inputs.add("TMAX")
        if out["tmin"].notna().any():
            available_inputs.add("TMIN")
        if out["awnd"].notna().any():
            available_inputs.add("AWND")
        if out["snow"].notna().any():
            available_inputs.add("SNOW")
        if out["snwd"].notna().any():
            available_inputs.add("SNWD")
        frames.append(out)

    if not frames:
        empty = pd.DataFrame(columns=["site_id", "date", "prcp", "tmax", "tmin", "awnd", "snow", "snwd"])
        return empty, set()

    merged = pd.concat(frames, ignore_index=True)
    merged["site_id"] = merged["site_id"].astype("string").str.strip()
    merged = merged.dropna(subset=["site_id", "date"]).sort_values(["site_id", "date"]).reset_index(drop=True)
    merged = merged.drop_duplicates(subset=["site_id", "date"], keep="last")
    return merged, available_inputs


def merge_weather_into_site_discharge(
    sdf: pd.DataFrame,
    precip_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Left-join NOAA daily columns onto a single-site USGS frame and apply the same post-merge
    numeric fills as `_add_features_per_site` (before lag/rolling features).

    Exposed for tests that must extract 7-day windows for API parity checks.
    """
    sdf = sdf.sort_values("date").copy()
    weather_cols = ["prcp", "tmax", "tmin", "awnd", "snow", "snwd"]

    if precip_df is not None:
        p = precip_df.copy()
        p["date"] = pd.to_datetime(p["date"], errors="coerce")
        if "precip_mm" in p.columns and "prcp" not in p.columns:
            p["prcp"] = p["precip_mm"]
        for c in weather_cols:
            if c not in p.columns:
                p[c] = pd.NA
            p[c] = pd.to_numeric(p[c], errors="coerce")
        p = p.dropna(subset=["date"])
        sdf = sdf.merge(p[["date"] + weather_cols], on="date", how="left")
    else:
        for c in weather_cols:
            sdf[c] = pd.NA

    sdf["prcp"] = pd.to_numeric(sdf["prcp"], errors="coerce").fillna(0.0)
    sdf["tmax"] = pd.to_numeric(sdf["tmax"], errors="coerce").fillna(0.0)
    sdf["tmin"] = pd.to_numeric(sdf["tmin"], errors="coerce").fillna(0.0)
    sdf["awnd"] = pd.to_numeric(sdf["awnd"], errors="coerce").fillna(0.0)
    sdf["snow"] = pd.to_numeric(sdf["snow"], errors="coerce").fillna(0.0)
    sdf["snow_depth"] = pd.to_numeric(sdf["snwd"], errors="coerce").fillna(0.0)
    return sdf


def _add_features_per_site(
    sdf: pd.DataFrame,
    precip_df: pd.DataFrame | None = None,
    *,
    heavy_rain_threshold: float = 20.0,
) -> pd.DataFrame:
    sdf = merge_weather_into_site_discharge(sdf, precip_df)

    sdf["discharge_lag1"] = sdf["discharge"].shift(1)
    sdf["discharge_lag2"] = sdf["discharge"].shift(2)
    sdf["discharge_lag3"] = sdf["discharge"].shift(3)

    sdf["discharge_roll_mean_3"] = sdf["discharge"].rolling(window=3, min_periods=3).mean()
    sdf["discharge_roll_mean_7"] = sdf["discharge"].rolling(window=7, min_periods=7).mean()

    sdf["discharge_diff_1"] = sdf["discharge"] - sdf["discharge_lag1"]
    sdf["month"] = sdf["date"].dt.month.astype(int)

    sdf["prcp_lag1"] = sdf["prcp"].shift(1)
    sdf["prcp_lag2"] = sdf["prcp"].shift(2)
    sdf["prcp_lag3"] = sdf["prcp"].shift(3)
    sdf["prcp_roll_sum_3"] = sdf["prcp"].rolling(3, min_periods=1).sum()
    sdf["prcp_roll_sum_7"] = sdf["prcp"].rolling(7, min_periods=1).sum()
    sdf["prcp_roll_mean_3"] = sdf["prcp"].rolling(3, min_periods=1).mean()
    sdf["prcp_roll_mean_7"] = sdf["prcp"].rolling(7, min_periods=1).mean()
    sdf["heavy_rain_flag_1d"] = (sdf["prcp"] > float(heavy_rain_threshold)).astype(int)

    sdf["tavg"] = (sdf["tmax"] + sdf["tmin"]) / 2.0
    sdf["temp_range"] = sdf["tmax"] - sdf["tmin"]

    sdf["prcp_x_discharge_lag1"] = sdf["prcp"] * sdf["discharge_lag1"]
    sdf["prcp_roll_sum_3_x_discharge_roll_mean_3"] = sdf["prcp_roll_sum_3"] * sdf["discharge_roll_mean_3"]
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
    heavy_rain_threshold: float = 20.0,
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
    noaa_df, available_weather_inputs = load_noaa_weather(noaa_dir)

    parts: list[pd.DataFrame] = []
    for site_id, sdf in df.groupby("site_id", sort=True):
        weather_site = None
        if not noaa_df.empty:
            weather_site = noaa_df.loc[noaa_df["site_id"] == str(site_id), ["date", "prcp", "tmax", "tmin", "awnd", "snow", "snwd"]]
            if weather_site.empty:
                weather_site = None
        sdf = _add_features_per_site(sdf, precip_df=weather_site, heavy_rain_threshold=heavy_rain_threshold)
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

    generated_weather_features = [
        "prcp_lag1",
        "prcp_lag2",
        "prcp_lag3",
        "prcp_roll_sum_3",
        "prcp_roll_sum_7",
        "prcp_roll_mean_3",
        "prcp_roll_mean_7",
        "heavy_rain_flag_1d",
        "tmax",
        "tmin",
        "tavg",
        "temp_range",
        "awnd",
        "snow",
        "snow_depth",
        "prcp_x_discharge_lag1",
        "prcp_roll_sum_3_x_discharge_roll_mean_3",
    ]
    unavailable_inputs = sorted({"PRCP", "TMAX", "TMIN", "AWND", "SNOW", "SNWD"} - set(available_weather_inputs))
    print("Generated NOAA-derived features:", ", ".join(generated_weather_features))
    print("Unavailable NOAA source columns:", ", ".join(unavailable_inputs) if unavailable_inputs else "none")
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate feature matrix and binary target from clean_data.csv.")
    p.add_argument("--clean-path", type=str, default="data/processed/clean_data.csv", help="Input clean dataset CSV")
    p.add_argument("--out-path", type=str, default="data/processed/features.csv", help="Output features CSV")
    p.add_argument("--percentile", type=float, default=0.9, help="Per-site discharge percentile threshold for target (e.g., 0.9)")
    p.add_argument("--noaa-dir", type=str, default="data/raw/noaa", help="Directory containing NOAA weather CSV files")
    p.add_argument("--heavy-rain-threshold", type=float, default=20.0, help="Threshold (mm/day) for heavy_rain_flag_1d")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    out = build_features_dataset(
        clean_path=args.clean_path,
        out_path=args.out_path,
        percentile=args.percentile,
        noaa_dir=args.noaa_dir,
        heavy_rain_threshold=args.heavy_rain_threshold,
    )
    print(f"Wrote features dataset: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

