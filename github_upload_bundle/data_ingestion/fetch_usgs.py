from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from data_ingestion.utils import ensure_dir, get_logger, parse_ymd, read_sites_config, request_json


USGS_DV_URL = "https://waterservices.usgs.gov/nwis/dv/"
USGS_SOURCE = "USGS_NWIS_DV"

# USGS parameter codes:
# - 00060: Discharge, cubic feet per second (ft3/s)
# - 00065: Gage height, feet (ft)
PARAM_DISCHARGE = "00060"
PARAM_STAGE = "00065"

OUTPUT_COLUMNS = ["site_id", "date", "discharge", "stage", "source"]


def _normalize_usgs_output(df: pd.DataFrame) -> pd.DataFrame:
    """
    Light-touch output normalization (do not change ingestion logic):
    - date strictly YYYY-MM-DD (date component only)
    - numeric discharge/stage (coerce errors to NaN)
    - sorted by site_id/date
    - drop duplicates
    """
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    out = df.copy()
    out["site_id"] = out["site_id"].astype(str).str.strip()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["discharge"] = pd.to_numeric(out.get("discharge"), errors="coerce")
    out["stage"] = pd.to_numeric(out.get("stage"), errors="coerce")
    if "source" not in out.columns:
        out["source"] = USGS_SOURCE

    out = out.dropna(subset=["site_id", "date"])
    out = out.drop_duplicates(subset=["site_id", "date"], keep="last")
    out = out.sort_values(["site_id", "date"]).reset_index(drop=True)
    return out[OUTPUT_COLUMNS]


def _extract_timeseries_values(series: dict[str, Any]) -> pd.DataFrame:
    """
    Convert one USGS JSON timeseries into a DataFrame with columns:
      - date (YYYY-MM-DD as pandas Timestamp normalized to date)
      - value (float)
      - parameter_cd (str)
      - site_id (str)
    """
    site_id = series.get("sourceInfo", {}).get("siteCode", [{}])[0].get("value")
    variable = series.get("variable", {})
    parameter_cd = variable.get("variableCode", [{}])[0].get("value")

    values_blocks = series.get("values", [])
    if not values_blocks or not values_blocks[0].get("value"):
        return pd.DataFrame(columns=["site_id", "date", "parameter_cd", "value"])

    rows = values_blocks[0]["value"]
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["site_id", "date", "parameter_cd", "value"])

    if "dateTime" not in df.columns or "value" not in df.columns:
        return pd.DataFrame(columns=["site_id", "date", "parameter_cd", "value"])

    df["date"] = pd.to_datetime(df["dateTime"], errors="coerce", utc=True).dt.date
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date"])

    df["site_id"] = site_id
    df["parameter_cd"] = parameter_cd
    return df[["site_id", "date", "parameter_cd", "value"]]


def fetch_usgs_daily_site(
    site_id: str,
    *,
    start_date: date,
    end_date: date,
    include_stage: bool = True,
    logger_name: str = "usgs",
) -> pd.DataFrame:
    """
    Fetch USGS Daily Values (dv) for one site and return a tidy DataFrame:
      site_id, date, discharge, stage, source
    """
    logger = get_logger(logger_name)

    param_cds = [PARAM_DISCHARGE] + ([PARAM_STAGE] if include_stage else [])
    params = {
        "format": "json",
        "sites": site_id,
        "startDT": start_date.isoformat(),
        "endDT": end_date.isoformat(),
        "parameterCd": ",".join(param_cds),
        "siteStatus": "all",
    }

    logger.info("Fetching USGS DV. site_id=%s start=%s end=%s params=%s", site_id, start_date, end_date, params["parameterCd"])
    payload = request_json(USGS_DV_URL, params=params, logger=logger)

    ts = payload.get("value", {}).get("timeSeries", [])
    if not ts:
        logger.warning("Empty USGS response. site_id=%s start=%s end=%s", site_id, start_date, end_date)
        return pd.DataFrame(columns=["site_id", "date", "discharge", "stage", "source"])

    parts = [_extract_timeseries_values(s) for s in ts]
    long_df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if long_df.empty:
        logger.warning("No usable datapoints after parsing. site_id=%s", site_id)
        return pd.DataFrame(columns=["site_id", "date", "discharge", "stage", "source"])

    wide = (
        long_df.pivot_table(
            index=["site_id", "date"],
            columns="parameter_cd",
            values="value",
            aggfunc="mean",
        )
        .reset_index()
        .rename(
            columns={
                PARAM_DISCHARGE: "discharge",
                PARAM_STAGE: "stage",
            }
        )
    )

    if "discharge" not in wide.columns:
        wide["discharge"] = pd.NA
    if "stage" not in wide.columns:
        wide["stage"] = pd.NA

    wide["source"] = USGS_SOURCE
    return _normalize_usgs_output(wide)


def fetch_usgs_daily(
    site_ids: list[str],
    *,
    start_date: date,
    end_date: date,
    include_stage: bool = True,
) -> pd.DataFrame:
    logger = get_logger("usgs")
    frames: list[pd.DataFrame] = []
    for site_id in site_ids:
        try:
            frames.append(
                fetch_usgs_daily_site(
                    site_id,
                    start_date=start_date,
                    end_date=end_date,
                    include_stage=include_stage,
                )
            )
        except Exception as e:
            logger.error("Failed to fetch site. site_id=%s error=%s", site_id, e)
    if not frames:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    out = pd.concat(frames, ignore_index=True)
    return _normalize_usgs_output(out)


def save_raw_usgs(
    df: pd.DataFrame,
    *,
    out_dir: str | Path,
    filename: str,
) -> Path:
    out_dir = ensure_dir(out_dir)
    path = out_dir / filename
    df.to_csv(path, index=False)
    return path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fetch daily USGS (NWIS DV) river data for one or more sites.")
    p.add_argument("--sites-config", type=str, default="data_ingestion/sites.json", help="Path to sites.json")
    p.add_argument("--start-date", type=str, required=True, help="YYYY-MM-DD")
    p.add_argument("--end-date", type=str, required=True, help="YYYY-MM-DD")
    p.add_argument("--out-dir", type=str, default="data/raw/usgs", help="Output directory for raw USGS CSVs")
    p.add_argument("--include-stage", action="store_true", help="Also fetch gage height (00065) if available")
    p.add_argument("--per-site", action="store_true", help="Also write one CSV per site_id")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    logger = get_logger("usgs")

    start = parse_ymd(args.start_date)
    end = parse_ymd(args.end_date)
    if end < start:
        raise ValueError("end-date must be >= start-date")

    sites = read_sites_config(args.sites_config)
    site_ids = [s["site_id"] for s in sites]

    df = fetch_usgs_daily(site_ids, start_date=start, end_date=end, include_stage=bool(args.include_stage))
    if df.empty:
        logger.warning("No data fetched for any site. Nothing written.")
        return 2
    for site_id, sdf in df.groupby("site_id", sort=True):
        logger.info("Fetched rows for site_id=%s rows=%s", site_id, len(sdf))

    combined_name = f"usgs_dv_daily_{start.isoformat()}_{end.isoformat()}.csv"
    combined_path = save_raw_usgs(df, out_dir=args.out_dir, filename=combined_name)
    logger.info("Wrote combined raw USGS data: %s (rows=%s)", combined_path.as_posix(), len(df))

    if args.per_site:
        for site_id, sdf in df.groupby("site_id", sort=True):
            fname = f"usgs_dv_daily_{site_id}_{start.isoformat()}_{end.isoformat()}.csv"
            pth = save_raw_usgs(sdf, out_dir=args.out_dir, filename=fname)
            logger.info("Wrote site raw USGS data: %s (rows=%s)", pth.as_posix(), len(sdf))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

