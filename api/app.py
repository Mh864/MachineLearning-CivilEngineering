from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.predict import load_model_artifact, predict_from_recent_discharge
from api.predict_stage import load_stage_model_artifact, predict_next_stage


app = FastAPI(title="Flood Risk Prediction API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_artifact = None
_artifact_path: str | None = None
_stage_artifact = None
_stage_artifact_path: str | None = None
_API_START_TIME = time.time()

USGS_RAW_DIR = Path("data/raw/usgs")
NOAA_DIR = Path("data/raw/noaa")
LAST_REFRESH_STATUS_PATH = Path("results/ops/last_refresh_status.json")

# Lazy cache: all `usgs_dv_daily*.csv` files merged (deduped by site + date).
_usgs_merged_df: pd.DataFrame | None = None
_usgs_merged_mtime: float = 0.0


def _newest_usgs_csv_mtime() -> float:
    if not USGS_RAW_DIR.is_dir():
        return 0.0
    mtimes = [p.stat().st_mtime for p in USGS_RAW_DIR.glob("usgs_dv_daily*.csv")]
    return max(mtimes) if mtimes else 0.0


def _load_merged_usgs_daily() -> pd.DataFrame:
    """
    Merge every `usgs_dv_daily*.csv` under data/raw/usgs so /latest can serve any gauge
    that appears in any export (combined multi-site file and/or per-site files).
    """
    if not USGS_RAW_DIR.is_dir():
        return pd.DataFrame()

    paths = sorted(USGS_RAW_DIR.glob("usgs_dv_daily*.csv"))
    frames: list[pd.DataFrame] = []
    for p in paths:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if not {"site_id", "date", "discharge"}.issubset(df.columns):
            continue
        if df.empty:
            continue
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out["site_key"] = _normalize_usgs_site_column(out["site_id"])
    out["date_parsed"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["site_key", "date_parsed"])
    out = out.sort_values(["site_key", "date_parsed"])
    out = out.drop_duplicates(subset=["site_key", "date_parsed"], keep="last")
    return out.reset_index(drop=True)


def _get_merged_usgs() -> pd.DataFrame:
    """Reload merged frame when any matching CSV on disk is newer than the cache."""
    global _usgs_merged_df, _usgs_merged_mtime
    newest = _newest_usgs_csv_mtime()
    if _usgs_merged_df is None or newest > _usgs_merged_mtime:
        _usgs_merged_df = _load_merged_usgs_daily()
        _usgs_merged_mtime = newest
    return _usgs_merged_df

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


def _load_artifact_pair() -> tuple[Any, str]:
    """Prefer LightGBM artifact if present, else logistic Pipeline artifact."""
    for path in ["models/lgbm_model.pkl", "models/model.pkl"]:
        if Path(path).exists():
            return load_model_artifact(path), path
    raise FileNotFoundError("No model file found in models/")


def _normalize_site_id_key(site_id: str) -> str:
    s = site_id.strip()
    try:
        return str(int(s)).zfill(8)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid site_id: {site_id!r}") from e


def _parse_optional_float_list(value: Optional[str]) -> list[float] | None:
    if value is None or str(value).strip() == "":
        return None
    out = [float(x.strip()) for x in str(value).split(",") if x.strip() != ""]
    return out if out else None


def _normalize_usgs_site_column(series: pd.Series) -> pd.Series:
    """Match CSV site_id whether stored as 1646500, 1646500.0, or 01646500."""

    def one(v) -> str:
        if pd.isna(v):
            return ""
        try:
            return str(int(float(v))).zfill(8)
        except (ValueError, TypeError):
            t = str(v).strip()
            try:
                return str(int(t)).zfill(8)
            except ValueError:
                return t.zfill(8)

    return series.map(one)


@app.on_event("startup")
def _startup() -> None:
    global _artifact, _artifact_path, _stage_artifact, _stage_artifact_path
    _artifact, _artifact_path = _load_artifact_pair()
    stage_path = Path("models/stage_model.pkl")
    if stage_path.exists():
        _stage_artifact = load_stage_model_artifact(stage_path.as_posix())
        _stage_artifact_path = stage_path.as_posix()


@app.get("/health")
def health() -> dict:
    """Liveness/readiness probe and simple deployment metadata."""
    out: dict[str, Any] = {
        "status": "ok",
        "model_loaded": _artifact is not None,
        "artifact_path": _artifact_path,
        "stage_model_loaded": _stage_artifact is not None,
        "stage_artifact_path": _stage_artifact_path,
        "uptime_seconds": round(time.time() - _API_START_TIME, 3),
    }
    if _artifact is not None:
        cal = _artifact.get("calibration")
        if cal:
            out["calibration"] = cal
    if LAST_REFRESH_STATUS_PATH.exists():
        try:
            out["last_refresh"] = json.loads(LAST_REFRESH_STATUS_PATH.read_text(encoding="utf-8"))
        except Exception:
            out["last_refresh"] = {"status": "unknown", "reason": "Could not parse refresh status file."}
    return out


@app.get("/latest")
def get_latest(
    site_id: str = Query(..., description="USGS site ID"),
    end_date: Optional[str] = Query(
        None,
        description="YYYY-MM-DD: last day of the 7-day window (inclusive). Defaults to the latest date available for this gauge.",
    ),
):
    site_norm = _normalize_site_id_key(site_id)

    usgs = _get_merged_usgs()
    if usgs.empty:
        raise HTTPException(
            status_code=404,
            detail="No USGS daily CSVs found under data/raw/usgs/ (expected usgs_dv_daily*.csv).",
        )

    site_all = usgs[usgs["site_key"] == site_norm].copy()

    if site_all.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No USGS rows for site {site_id} in data/raw/usgs/. "
                "The bundled file may only include some gauges. Fetch all sites with: "
                "python -m data_ingestion.fetch_usgs --start-date 2018-01-01 --end-date 2024-12-31 --include-stage"
            ),
        )

    site_all = site_all.dropna(subset=["date_parsed"]).sort_values("date_parsed")

    if len(site_all) < 7:
        raise HTTPException(
            status_code=404,
            detail=f"Not enough data for site {site_id}: need at least 7 daily rows, found {len(site_all)}.",
        )

    data_start = site_all["date_parsed"].iloc[0].strftime("%Y-%m-%d")
    data_end = site_all["date_parsed"].iloc[-1].strftime("%Y-%m-%d")

    if end_date is not None and str(end_date).strip() != "":
        try:
            end_dt = pd.to_datetime(end_date, errors="raise").normalize()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid end_date: {end_date!r}") from e
        site_window = site_all[site_all["date_parsed"] <= end_dt].copy()
        if len(site_window) < 7:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Not enough USGS rows on or before {end_date} for site {site_id}: "
                    f"need 7 days, found {len(site_window)}. "
                    f"Data span for this gauge: {data_start} to {data_end}."
                ),
            )
        site_data = site_window.tail(7)
    else:
        site_data = site_all.tail(7)

    dates_dt = site_data["date_parsed"].dt.normalize()
    dates = [d.strftime("%Y-%m-%d") for d in dates_dt]
    discharge_values = [round(float(v), 1) for v in site_data["discharge"].tolist()]
    stage_series = site_data["stage"] if "stage" in site_data.columns else pd.Series([pd.NA] * len(site_data), index=site_data.index)
    stage_values_raw = pd.to_numeric(stage_series, errors="coerce")
    stage_available = bool(stage_values_raw.notna().any())
    stage_values = [None if pd.isna(v) else round(float(v), 2) for v in stage_values_raw.tolist()]

    noaa_slug = SITE_TO_NOAA.get(site_norm)
    rainfall_available = False
    rainfall_mm = [0.0] * 7
    tmax_c = [0.0] * 7
    tmin_c = [0.0] * 7
    awnd = [0.0] * 7
    snow = [0.0] * 7
    snow_depth = [0.0] * 7
    weather_available = False

    if noaa_slug:
        noaa_path = NOAA_DIR / f"rainfall_{noaa_slug}.csv"
        if noaa_path.exists():
            noaa = pd.read_csv(noaa_path)
            if "DATE" not in noaa.columns or "PRCP" not in noaa.columns:
                rainfall_available = False
            else:
                rainfall_available = True
                weather_available = True
                noaa = noaa.copy()
                noaa["date_parsed"] = pd.to_datetime(noaa["DATE"], errors="coerce")
                noaa["PRCP"] = pd.to_numeric(noaa["PRCP"], errors="coerce").fillna(0.0)
                noaa["day"] = noaa["date_parsed"].dt.strftime("%Y-%m-%d")
                prcp_by_date = dict(zip(noaa["day"], noaa["PRCP"]))
                tmax_by_date: dict[str, float] = {}
                tmin_by_date: dict[str, float] = {}
                awnd_by_date: dict[str, float] = {}
                snow_by_date: dict[str, float] = {}
                snwd_by_date: dict[str, float] = {}
                if "TMAX" in noaa.columns:
                    noaa["TMAX"] = pd.to_numeric(noaa["TMAX"], errors="coerce").fillna(0.0)
                    tmax_by_date = dict(zip(noaa["day"], noaa["TMAX"]))
                if "TMIN" in noaa.columns:
                    noaa["TMIN"] = pd.to_numeric(noaa["TMIN"], errors="coerce").fillna(0.0)
                    tmin_by_date = dict(zip(noaa["day"], noaa["TMIN"]))
                if "AWND" in noaa.columns:
                    noaa["AWND"] = pd.to_numeric(noaa["AWND"], errors="coerce").fillna(0.0)
                    awnd_by_date = dict(zip(noaa["day"], noaa["AWND"]))
                if "SNOW" in noaa.columns:
                    noaa["SNOW"] = pd.to_numeric(noaa["SNOW"], errors="coerce").fillna(0.0)
                    snow_by_date = dict(zip(noaa["day"], noaa["SNOW"]))
                if "SNWD" in noaa.columns:
                    noaa["SNWD"] = pd.to_numeric(noaa["SNWD"], errors="coerce").fillna(0.0)
                    snwd_by_date = dict(zip(noaa["day"], noaa["SNWD"]))
                if not tmax_by_date and not tmin_by_date:
                    weather_available = False
                for i, d in enumerate(dates_dt):
                    day_key = pd.Timestamp(d).strftime("%Y-%m-%d")
                    rainfall_mm[i] = round(float(prcp_by_date.get(day_key, 0.0)), 1)
                    tmax_c[i] = round(float(tmax_by_date.get(day_key, 0.0)), 1)
                    tmin_c[i] = round(float(tmin_by_date.get(day_key, 0.0)), 1)
                    awnd[i] = round(float(awnd_by_date.get(day_key, 0.0)), 3)
                    snow[i] = round(float(snow_by_date.get(day_key, 0.0)), 1)
                    snow_depth[i] = round(float(snwd_by_date.get(day_key, 0.0)), 1)

    latest_date = dates[-1]

    return {
        "site_id": site_norm,
        "dates": dates,
        "discharge": discharge_values,
        "stage": stage_values,
        "stage_available": stage_available,
        "rainfall_mm": rainfall_mm,
        "rainfall_available": rainfall_available,
        "tmax_c": tmax_c,
        "tmin_c": tmin_c,
        "awnd": awnd,
        "snow": snow,
        "snow_depth": snow_depth,
        "weather_available": weather_available,
        "latest_date": latest_date,
        "data_start": data_start,
        "data_end": data_end,
    }


@app.get("/predict")
def predict(
    site_id: str = Query(..., description="USGS site id (traceability; not always used as a model feature)"),
    recent_discharge: str = Query(
        ...,
        description="Comma-separated discharge values ordered oldest->newest (need >=7).",
    ),
    as_of_date: Optional[str] = Query(None, description="YYYY-MM-DD used for month feature; defaults to today (UTC)."),
    recent_prcp: Optional[str] = Query(
        None,
        description="Optional comma-separated rainfall (mm) for the same days as discharge window (>=7 values).",
    ),
    tmax: Optional[str] = Query(None, description="Reserved: optional comma-separated TMAX series."),
    tmin: Optional[str] = Query(None, description="Reserved: optional comma-separated TMIN series."),
    awnd: Optional[str] = Query(None, description="Reserved: optional comma-separated wind series."),
    snow: Optional[str] = Query(None, description="Reserved: optional comma-separated snow series."),
    snow_depth: Optional[str] = Query(None, description="Reserved: optional comma-separated snow depth series."),
    heavy_rain_threshold: Optional[float] = Query(None, description="Reserved: heavy rain threshold (mm)."),
):
    global _artifact, _artifact_path
    if _artifact is None:
        _artifact, _artifact_path = _load_artifact_pair()

    recent = [float(x.strip()) for x in recent_discharge.split(",") if x.strip() != ""]
    if len(recent) < 7:
        raise HTTPException(
            status_code=400,
            detail="recent_discharge must contain at least 7 comma-separated numeric values (oldest to newest).",
        )

    prcp_list: list[float] | None = None
    if recent_prcp is not None and recent_prcp.strip() != "":
        prcp_list = [float(x.strip()) for x in recent_prcp.split(",") if x.strip() != ""]
        if len(prcp_list) < 7:
            prcp_list = None

    result = predict_from_recent_discharge(
        artifact=_artifact,
        site_id=site_id,
        recent_discharge=recent,
        as_of_date=as_of_date,
        recent_prcp=prcp_list,
        recent_tmax=_parse_optional_float_list(tmax),
        recent_tmin=_parse_optional_float_list(tmin),
        recent_awnd=_parse_optional_float_list(awnd),
        recent_snow=_parse_optional_float_list(snow),
        recent_snow_depth=_parse_optional_float_list(snow_depth),
        heavy_rain_threshold=heavy_rain_threshold,
    )

    response = {
        "site_id": site_id,
        "prediction": int(result["prediction"]),
        "probability": result["probability"],
    }
    if isinstance(result["probability"], float):
        response["risk_label"] = "high" if int(result["prediction"]) == 1 else "normal"
    return response


@app.get("/predict-stage")
def predict_stage(
    site_id: str = Query(..., description="USGS site id"),
    recent_stage: str = Query(
        ...,
        description="Comma-separated recent stage values (oldest->newest, need >=7).",
    ),
    recent_discharge: Optional[str] = Query(
        None,
        description="Optional comma-separated discharge values aligned to stage window (>=7).",
    ),
    as_of_date: Optional[str] = Query(None, description="YYYY-MM-DD for month feature; defaults to today (UTC)."),
    recent_prcp: Optional[str] = Query(None, description="Optional comma-separated rainfall series."),
    tmax: Optional[str] = Query(None, description="Optional comma-separated TMAX series."),
    tmin: Optional[str] = Query(None, description="Optional comma-separated TMIN series."),
):
    global _stage_artifact, _stage_artifact_path
    if _stage_artifact is None:
        stage_path = Path("models/stage_model.pkl")
        if not stage_path.exists():
            raise HTTPException(status_code=404, detail="Stage model artifact not found: models/stage_model.pkl")
        _stage_artifact = load_stage_model_artifact(stage_path.as_posix())
        _stage_artifact_path = stage_path.as_posix()

    recent_stage_vals = [float(x.strip()) for x in recent_stage.split(",") if x.strip() != ""]
    if len(recent_stage_vals) < 7:
        raise HTTPException(
            status_code=400,
            detail="recent_stage must contain at least 7 comma-separated numeric values (oldest to newest).",
        )

    discharge_vals = _parse_optional_float_list(recent_discharge)
    prcp_vals = _parse_optional_float_list(recent_prcp)
    tmax_vals = _parse_optional_float_list(tmax)
    tmin_vals = _parse_optional_float_list(tmin)
    pred_stage = predict_next_stage(
        artifact=_stage_artifact,
        recent_stage=recent_stage_vals,
        as_of_date=as_of_date,
        recent_discharge=discharge_vals,
        recent_prcp=prcp_vals,
        recent_tmax=tmax_vals,
        recent_tmin=tmin_vals,
    )
    return {
        "site_id": site_id,
        "predicted_stage_next_day": float(pred_stage),
        "units": "ft",
    }
