from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from data_ingestion.utils import ensure_dir, get_logger, parse_ymd, read_sites_config, request_json


NOAA_SOURCE = "NOAA_CDO_GHCND"
NOAA_CDO_URL = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"

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

# GHCND station IDs (can be overridden in sites.json with "noaa_station_id")
SITE_TO_STATION = {
    "01646500": "GHCND:USW00013743",  # Washington Reagan, DC
    "02087500": "GHCND:USW00013722",  # Raleigh-Durham, NC
    "03015500": "GHCND:USW00014735",  # Bradford, PA
    "05054000": "GHCND:USW00014914",  # Fargo, ND
    "06710247": "GHCND:USW00023062",  # Denver, CO
    "08066500": "GHCND:USW00012960",  # Houston/IAH, TX
    "09380000": "GHCND:USW00023195",  # Page, AZ
    "11425500": "GHCND:USW00023232",  # Sacramento, CA (regional GHCND; aligns with sites.json)
    "12301933": "GHCND:USW00024153",  # Missoula, MT
    "14211720": "GHCND:USW00024229",  # Portland, OR
}


def _iter_date_windows(start_date: date, end_date: date, max_days: int = 364) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    cur = start_date
    while cur <= end_date:
        win_end = min(cur + timedelta(days=max_days - 1), end_date)
        windows.append((cur, win_end))
        cur = win_end + timedelta(days=1)
    return windows


def _fetch_station_daily(
    *,
    station_id: str,
    start_date: date,
    end_date: date,
    token: str,
    logger_name: str = "noaa",
) -> pd.DataFrame:
    logger = get_logger(logger_name)
    headers = {"token": token}

    rows: list[dict[str, Any]] = []
    for win_start, win_end in _iter_date_windows(start_date, end_date, max_days=364):
        offset = 1
        limit = 1000
        while True:
            params = {
                "datasetid": "GHCND",
                "stationid": station_id,
                "startdate": win_start.isoformat(),
                "enddate": win_end.isoformat(),
                "datatypeid": ["PRCP", "TMAX", "TMIN"],
                "units": "metric",
                "limit": limit,
                "offset": offset,
            }
            payload = request_json(NOAA_CDO_URL, params=params, headers=headers, logger=logger)
            results = payload.get("results", [])
            if not results:
                break
            rows.extend(results)
            if len(results) < limit:
                break
            offset += limit

    if not rows:
        return pd.DataFrame(columns=["STATION", "NAME", "DATE", "PRCP", "TMAX", "TMIN"])

    long = pd.DataFrame(rows)
    if long.empty:
        return pd.DataFrame(columns=["STATION", "NAME", "DATE", "PRCP", "TMAX", "TMIN"])

    keep_cols = [c for c in ["station", "name", "date", "datatype", "value"] if c in long.columns]
    long = long[keep_cols]
    if set(["station", "date", "datatype", "value"]) - set(long.columns):
        return pd.DataFrame(columns=["STATION", "NAME", "DATE", "PRCP", "TMAX", "TMIN"])
    if "name" not in long.columns:
        long["name"] = station_id

    long["DATE"] = pd.to_datetime(long["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    long["VALUE"] = pd.to_numeric(long["value"], errors="coerce")
    long = long.dropna(subset=["DATE"]).copy()
    long["DATATYPE"] = long["datatype"].astype(str).str.upper()

    wide = (
        long.pivot_table(
            index=["DATE", "station", "name"],
            columns="DATATYPE",
            values="VALUE",
            aggfunc="first",
        )
        .reset_index()
        .rename(columns={"station": "STATION", "name": "NAME"})
    )
    for c in ["PRCP", "TMAX", "TMIN"]:
        if c not in wide.columns:
            wide[c] = pd.NA

    out = wide[["STATION", "NAME", "DATE", "PRCP", "TMAX", "TMIN"]].copy()
    out["PRCP"] = pd.to_numeric(out["PRCP"], errors="coerce").fillna(0.0)
    out["TMAX"] = pd.to_numeric(out["TMAX"], errors="coerce")
    out["TMIN"] = pd.to_numeric(out["TMIN"], errors="coerce")
    out = out.sort_values("DATE").reset_index(drop=True)
    return out


def fetch_weather_daily(
    sites: list[dict[str, Any]],
    *,
    start_date: date,
    end_date: date,
    token: str,
) -> pd.DataFrame:
    logger = get_logger("noaa")
    parts: list[pd.DataFrame] = []

    for site in sites:
        site_id = str(site["site_id"])
        location_name = SITE_TO_NOAA.get(site_id, site_id)
        station_id = str(site.get("noaa_station_id") or SITE_TO_STATION.get(site_id, "")).strip()
        if not station_id:
            logger.warning("No NOAA station mapping for site_id=%s. Skipping.", site_id)
            continue

        try:
            sdf = _fetch_station_daily(
                station_id=station_id,
                start_date=start_date,
                end_date=end_date,
                token=token,
                logger_name="noaa",
            )
        except Exception as e:
            logger.error("Failed NOAA fetch. site_id=%s station=%s error=%s", site_id, station_id, e)
            continue

        if sdf.empty:
            logger.warning("No NOAA rows returned. site_id=%s station=%s", site_id, station_id)
            continue

        sdf["site_id"] = site_id
        sdf["location_name"] = location_name
        sdf["source"] = NOAA_SOURCE
        parts.append(sdf)
        logger.info("Fetched NOAA rows. site_id=%s station=%s rows=%s", site_id, station_id, len(sdf))

    if not parts:
        return pd.DataFrame(columns=["site_id", "date", "precip_mm", "tmin_c", "tmax_c", "source"])

    all_df = pd.concat(parts, ignore_index=True)
    out = pd.DataFrame(
        {
            "site_id": all_df["site_id"],
            "date": pd.to_datetime(all_df["DATE"], errors="coerce").dt.strftime("%Y-%m-%d"),
            "precip_mm": pd.to_numeric(all_df["PRCP"], errors="coerce").fillna(0.0),
            "tmin_c": pd.to_numeric(all_df["TMIN"], errors="coerce"),
            "tmax_c": pd.to_numeric(all_df["TMAX"], errors="coerce"),
            "source": NOAA_SOURCE,
        }
    )
    out = out.dropna(subset=["site_id", "date"]).sort_values(["site_id", "date"]).reset_index(drop=True)
    return out


def save_raw_weather(df: pd.DataFrame, *, out_dir: str | Path, filename: str) -> Path:
    out_dir = ensure_dir(out_dir)
    path = out_dir / filename
    df.to_csv(path, index=False)
    return path


def save_rainfall_per_location(df: pd.DataFrame, *, out_dir: str | Path) -> list[Path]:
    out_dir = ensure_dir(out_dir)
    paths: list[Path] = []
    for location_name, sdf in df.groupby("location_name", sort=True):
        out = sdf[["STATION", "NAME", "DATE", "PRCP", "TMAX", "TMIN"]].copy()
        out["PRCP"] = pd.to_numeric(out["PRCP"], errors="coerce").fillna(0.0)
        out = out.sort_values("DATE").reset_index(drop=True)
        filename = f"rainfall_{location_name}.csv"
        path = out_dir / filename
        out.to_csv(path, index=False)
        paths.append(path)
    return paths


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fetch daily NOAA CDO weather data for sites.")
    p.add_argument("--sites-config", type=str, default="data_ingestion/sites.json", help="Path to sites.json")
    p.add_argument("--start-date", type=str, required=True, help="YYYY-MM-DD")
    p.add_argument("--end-date", type=str, required=True, help="YYYY-MM-DD")
    p.add_argument("--out-dir", type=str, default="data/raw/noaa", help="Output directory for raw NOAA CSVs")
    p.add_argument("--token", type=str, default=None, help="NOAA CDO API token (optional if NOAA_CDO_TOKEN env is set)")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    logger = get_logger("noaa")

    start = parse_ymd(args.start_date)
    end = parse_ymd(args.end_date)
    if end < start:
        raise ValueError("end-date must be >= start-date")

    sites = read_sites_config(args.sites_config)
    token = args.token or os.getenv("NOAA_CDO_TOKEN", "").strip()
    if not token:
        raise ValueError("Missing NOAA token. Pass --token or set NOAA_CDO_TOKEN.")

    df = fetch_weather_daily(sites, start_date=start, end_date=end, token=token)
    if df.empty:
        logger.warning("No NOAA data fetched for configured sites.")
        return 2

    # Re-fetch per-site weather blocks for rainfall_<LocationName>.csv output.
    # This keeps files aligned with modeling/features.py expectations.
    weather_parts: list[pd.DataFrame] = []
    for site in sites:
        site_id = str(site["site_id"])
        location_name = SITE_TO_NOAA.get(site_id, site_id)
        station_id = str(site.get("noaa_station_id") or SITE_TO_STATION.get(site_id, "")).strip()
        if not station_id:
            continue
        try:
            sdf = _fetch_station_daily(
                station_id=station_id,
                start_date=start,
                end_date=end,
                token=token,
                logger_name="noaa",
            )
        except Exception:
            continue
        if sdf.empty:
            continue
        sdf["site_id"] = site_id
        sdf["location_name"] = location_name
        weather_parts.append(sdf)

    if weather_parts:
        weather_all = pd.concat(weather_parts, ignore_index=True)
        saved_paths = save_rainfall_per_location(weather_all, out_dir=args.out_dir)
        logger.info("Wrote rainfall files: %s", ", ".join([p.name for p in saved_paths]))

    fname = f"noaa_daily_{start.isoformat()}_{end.isoformat()}.csv"
    path = save_raw_weather(df, out_dir=args.out_dir, filename=fname)
    logger.info("Wrote combined NOAA data: %s (rows=%s)", path.as_posix(), len(df))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

