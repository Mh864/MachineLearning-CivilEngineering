from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


RAW_REQUIRED_COLUMNS = ["site_id", "date", "discharge", "stage", "source"]


def _read_raw_csvs(raw_dir: str | Path) -> pd.DataFrame:
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No raw USGS CSV files found in: {raw_dir.as_posix()}")

    frames: list[pd.DataFrame] = []
    for fp in files:
        df = pd.read_csv(fp, dtype={"site_id": "string"})
        missing = [c for c in RAW_REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns in {fp.name}: {missing}")
        frames.append(df[RAW_REQUIRED_COLUMNS])

    out = pd.concat(frames, ignore_index=True)
    return out


def _normalize_raw(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["site_id"] = out["site_id"].astype("string").str.strip()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["discharge"] = pd.to_numeric(out["discharge"], errors="coerce")
    out["stage"] = pd.to_numeric(out["stage"], errors="coerce")

    out = out.dropna(subset=["site_id", "date"])
    out = out.drop_duplicates(subset=["site_id", "date"], keep="last")
    out = out.sort_values(["site_id", "date"]).reset_index(drop=True)
    return out


def _reindex_continuous_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each site, ensure a continuous daily timeline between min(date) and max(date).
    Missing days are inserted with NaNs for discharge/stage/source.
    """
    parts: list[pd.DataFrame] = []
    for site_id, sdf in df.groupby("site_id", sort=True):
        sdf = sdf.sort_values("date").copy()
        idx = pd.date_range(sdf["date"].min(), sdf["date"].max(), freq="D")
        sdf = sdf.set_index("date").reindex(idx)
        sdf.index.name = "date"
        sdf = sdf.reset_index()
        sdf["site_id"] = site_id
        parts.append(sdf)

    out = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    # Keep a consistent column order for downstream steps
    out = out[RAW_REQUIRED_COLUMNS].sort_values(["site_id", "date"]).reset_index(drop=True)
    return out


def clean_usgs_raw_to_processed(
    *,
    raw_dir: str | Path = "data/raw/usgs",
    out_path: str | Path = "data/processed/clean_data.csv",
) -> Path:
    df = _read_raw_csvs(raw_dir)
    df = _normalize_raw(df)
    df = _reindex_continuous_daily(df)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Clean raw USGS files and output a continuous daily dataset.")
    p.add_argument("--raw-dir", type=str, default="data/raw/usgs", help="Directory containing raw USGS CSV files")
    p.add_argument("--out-path", type=str, default="data/processed/clean_data.csv", help="Output CSV path")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    out = clean_usgs_raw_to_processed(raw_dir=args.raw_dir, out_path=args.out_path)
    print(f"Wrote processed clean dataset: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

