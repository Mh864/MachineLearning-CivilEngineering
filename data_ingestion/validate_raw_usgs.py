"""
Validate raw USGS CSVs under data/raw/usgs after a fetch.

Checks: expected sites present, valid dates, numeric discharge, duplicates,
per-site date span vs row count (missing days before clean_data reindex).

Usage (from repo root):
  python -m data_ingestion.validate_raw_usgs
  python -m data_ingestion.validate_raw_usgs --raw-dir data/raw/usgs --strict
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from data_ingestion.utils import read_sites_config
from data_processing.clean_data import _normalize_raw, _read_raw_csvs


def _per_file_summary(raw_dir: Path) -> None:
    csvs = sorted(raw_dir.glob("*.csv"))
    print("Per-file (before merge):")
    for fp in csvs:
        df = pd.read_csv(fp, dtype={"site_id": "string"})
        dp = pd.to_datetime(df["date"], errors="coerce")
        dups = df.duplicated(subset=["site_id", "date"], keep=False).sum()
        sites = df["site_id"].astype(str).str.strip().nunique()
        print(
            f"  {fp.name}: rows={len(df)} sites={sites} bad_dates={dp.isna().sum()} "
            f"dup_rows={int(dups)}"
        )
    print()


def validate(
    *,
    raw_dir: Path,
    sites_config: Path,
    strict: bool = False,
    verbose: bool = False,
) -> int:
    expected = [s["site_id"] for s in read_sites_config(sites_config)]
    raw_dir = Path(raw_dir)

    if not raw_dir.is_dir():
        print(f"ERROR: raw dir not found: {raw_dir}", file=sys.stderr)
        return 2

    csvs = sorted(raw_dir.glob("*.csv"))
    if not csvs:
        print(f"ERROR: no CSV files in {raw_dir}", file=sys.stderr)
        return 2

    if verbose:
        _per_file_summary(raw_dir)

    merged = _read_raw_csvs(raw_dir)
    df = _normalize_raw(merged)

    print(f"Files read: {len(csvs)}  Rows after concat: {len(merged)}  After dedup: {len(df)}")
    if len(merged) > len(df):
        print(f"  (Dropped {len(merged) - len(df)} duplicate site-date rows from overlapping files.)")

    df = df.copy()
    df["site_key"] = df["site_id"].astype(str).str.strip()
    df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = int(df["date_parsed"].isna().sum())
    q = pd.to_numeric(df["discharge"], errors="coerce")
    nan_q = int(q.isna().sum())

    print(f"Invalid dates: {bad_dates}  NaN discharge: {nan_q}")
    if bad_dates or nan_q:
        print("WARNING: rows with bad dates or non-numeric discharge should be reviewed.", file=sys.stderr)

    have = set(df["site_key"].unique())
    missing = sorted(set(expected) - have)
    extra = sorted(have - set(expected))

    print(f"Expected sites: {len(expected)}  Present: {len(have)}")
    if missing:
        print(f"MISSING sites (in sites.json but not in raw data): {missing}")
    if extra:
        print(f"Extra sites (in raw but not in sites.json): {extra}")

    print("\nPer-site coverage (before clean_data gap-fill):")
    for site in sorted(have):
        sdf = df[df["site_key"] == site]
        dmin, dmax = sdf["date_parsed"].min(), sdf["date_parsed"].max()
        span = (dmax - dmin).days + 1 if pd.notna(dmin) else 0
        n = len(sdf)
        gap = span - n
        print(f"  {site}: rows={n}  span_days={span}  gap={gap}  {dmin.date()} .. {dmax.date()}")

    exit_code = 0
    if strict and (bad_dates or nan_q):
        exit_code = 1

    if missing:
        exit_code = 1
        print("\nFAIL: Not all configured gauges are present in raw USGS exports.")
        print("  Fix: fetch all sites for your date window, e.g.")
        print(
            "  python -m data_ingestion.fetch_usgs --sites-config data_ingestion/sites.json "
            "--start-date 2018-01-01 --end-date 2024-12-31 --out-dir data/raw/usgs --include-stage --per-site"
        )
        print("  Remove or archive small test CSVs in data/raw/usgs if they overlap dates (they dedupe, but add confusion).")
    elif not (bad_dates or nan_q):
        print("\nOK: All configured sites present; dates and discharge look usable.")

    return exit_code


def main() -> int:
    p = argparse.ArgumentParser(description="Validate raw USGS CSVs.")
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw/usgs"))
    p.add_argument("--sites-config", type=Path, default=Path("data_ingestion/sites.json"))
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any invalid dates or NaN discharge",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="List each CSV file before merge")
    args = p.parse_args()
    return validate(
        raw_dir=args.raw_dir,
        sites_config=args.sites_config,
        strict=args.strict,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
