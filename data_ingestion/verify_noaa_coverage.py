"""
Offline verification of NOAA CSV coverage vs configured USGS sites.

Checks that each expected `rainfall_<LocationName>.csv` exists under `data/raw/noaa`,
reports per-file date span and row counts, and flags gaps vs a target calendar range.

Usage (from repo root):
  python -m data_ingestion.verify_noaa_coverage --noaa-dir data/raw/noaa
  python -m data_ingestion.verify_noaa_coverage --noaa-dir data/raw/noaa \\
      --expected-start 2018-01-01 --expected-end 2024-12-31 --out-json results/noaa_coverage.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from data_ingestion.fetch_weather import SITE_TO_NOAA, SITE_TO_STATION
from data_ingestion.utils import parse_ymd, read_sites_config


def _date_gaps(sorted_dates: pd.Series) -> int:
    if sorted_dates.empty or len(sorted_dates) < 2:
        return 0
    d = pd.to_datetime(sorted_dates, errors="coerce").dropna().sort_values()
    if len(d) < 2:
        return 0
    return int((d.diff().dt.days > 1).sum())


def verify_noaa_coverage(
    *,
    noaa_dir: str | Path,
    sites_config: str | Path = "data_ingestion/sites.json",
    expected_start: date | None = None,
    expected_end: date | None = None,
) -> dict:
    noaa_dir = Path(noaa_dir)
    sites = read_sites_config(sites_config)
    expected_start = expected_start or date(2018, 1, 1)
    expected_end = expected_end or date(2024, 12, 31)

    sites_detail: list[dict] = []
    all_ok = True

    for site in sites:
        site_id = str(site["site_id"]).strip()
        loc = SITE_TO_NOAA.get(site_id)
        station = str(site.get("noaa_station_id") or SITE_TO_STATION.get(site_id, "")).strip()
        if not loc:
            sites_detail.append(
                {
                    "site_id": site_id,
                    "location_name": None,
                    "status": "error",
                    "detail": "Missing SITE_TO_NOAA mapping in fetch_weather.py",
                }
            )
            all_ok = False
            continue

        path = noaa_dir / f"rainfall_{loc}.csv"
        if not path.is_file():
            sites_detail.append(
                {
                    "site_id": site_id,
                    "location_name": loc,
                    "noaa_station_id": station or None,
                    "file": path.as_posix(),
                    "status": "missing_file",
                }
            )
            all_ok = False
            continue

        try:
            df = pd.read_csv(path)
        except Exception as e:
            sites_detail.append(
                {
                    "site_id": site_id,
                    "location_name": loc,
                    "file": path.as_posix(),
                    "status": "read_error",
                    "detail": str(e),
                }
            )
            all_ok = False
            continue

        col_date = "DATE" if "DATE" in df.columns else None
        if col_date is None:
            sites_detail.append(
                {
                    "site_id": site_id,
                    "location_name": loc,
                    "file": path.as_posix(),
                    "status": "bad_schema",
                    "detail": "Expected DATE column",
                }
            )
            all_ok = False
            continue

        dt = pd.to_datetime(df[col_date], errors="coerce").dropna()
        if dt.empty:
            sites_detail.append(
                {
                    "site_id": site_id,
                    "location_name": loc,
                    "file": path.as_posix(),
                    "status": "empty_dates",
                }
            )
            all_ok = False
            continue

        dmin = dt.min().date()
        dmax = dt.max().date()
        n_rows = len(df)
        gaps = _date_gaps(dt)
        covers_start = dmin <= expected_start
        covers_end = dmax >= expected_end
        ok_span = covers_start and covers_end

        if not ok_span:
            all_ok = False

        sites_detail.append(
            {
                "site_id": site_id,
                "location_name": loc,
                "noaa_station_id": station or None,
                "file": path.as_posix(),
                "status": "ok" if ok_span else "incomplete_range",
                "n_rows": n_rows,
                "date_min": dmin.isoformat(),
                "date_max": dmax.isoformat(),
                "expected_range_covered": ok_span,
                "internal_date_gaps_gt1d": gaps,
            }
        )

    return {
        "noaa_dir": noaa_dir.as_posix(),
        "expected_calendar_range": {
            "start": expected_start.isoformat(),
            "end": expected_end.isoformat(),
        },
        "mapping_source": "data_ingestion/fetch_weather.SITE_TO_NOAA + SITE_TO_STATION (overridable via sites.json noaa_station_id)",
        "all_sites_ok": all_ok,
        "sites": sites_detail,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Verify NOAA rainfall CSV files for all configured sites.")
    p.add_argument("--noaa-dir", type=str, default="data/raw/noaa")
    p.add_argument("--sites-config", type=str, default="data_ingestion/sites.json")
    p.add_argument("--expected-start", type=str, default="2018-01-01")
    p.add_argument("--expected-end", type=str, default="2024-12-31")
    p.add_argument("--out-json", type=str, default=None, help="Optional path to write full report JSON")
    p.add_argument(
        "--warn-only",
        action="store_true",
        help="Always exit 0 (still prints report; use in CI when coverage is informational).",
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    report = verify_noaa_coverage(
        noaa_dir=args.noaa_dir,
        sites_config=args.sites_config,
        expected_start=parse_ymd(args.expected_start),
        expected_end=parse_ymd(args.expected_end),
    )
    print(json.dumps(report, indent=2))
    if args.out_json:
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {out.as_posix()}")
    if args.warn_only:
        return 0
    return 0 if report["all_sites_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
